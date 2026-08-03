"""M3B.2.1 Step 2: 12-Stage Pipeline Funnel & Representative Signal Tracing Audit."""

import json
import logging
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.clock import HistoricalClock
from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.backtesting.execution import ExecutionSimulator, OrderIntent
from tradecraft.backtesting.portfolio import Portfolio
from tradecraft.backtesting.risk_hooks import BasicCapitalGuard
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.core.db import SessionLocal
from tradecraft.core.db_models import Instrument
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT
from tradecraft.strategy.base import ExitSignal, SignalIntent
from tradecraft.strategy.v2_strategies import (
    BaseV2Strategy,
    BreakoutConfirmV2Strategy,
    MeanReversionV2Strategy,
    MomentumRSV2Strategy,
    TrendPullbackV2Strategy,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3b_2_1_audit")


@dataclass
class FunnelCounts:
    eligible_observations: int = 0
    raw_setups: int = 0
    confirmed_signals: int = 0
    signal_intent_objects: int = 0
    risk_sizing_evaluations: int = 0
    accepted_intents: int = 0
    orders_constructed: int = 0
    orders_scheduled_t1: int = 0
    fill_attempts: int = 0
    successful_fills: int = 0
    positions_opened: int = 0
    completed_trades: int = 0


@dataclass
class SignalTraceRecord:
    family: str
    instrument_id: str
    symbol: str
    signal_date: str
    features: dict[str, Any]
    signal_intent_created: bool
    direction: str
    order_type: str
    stop_loss_level: float | None
    quantity_hint: int | None
    risk_hook_accepted: bool
    risk_hook_rejection_reason: str
    t1_date: str | None
    t1_open: float | None
    t1_high: float | None
    t1_low: float | None
    t1_close: float | None
    execution_fill_attempted: bool
    execution_filled: bool
    execution_rejection_reason: str
    final_trade_completed: bool


def audit_strategy_family(db: SessionLocal, strategy: BaseV2Strategy) -> tuple[FunnelCounts, dict[str, int], list[SignalTraceRecord]]:
    DevelopmentOnlyGuard.validate_range(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
    calendar = TradingCalendar()
    pit_universe = PointInTimeUniverse(db, index_name="NIFTY_50")
    clock = HistoricalClock(calendar, DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
    portal = DataPortal(db, pit_universe, DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)

    all_members = pit_universe.members(DEVELOPMENT_SPLIT.start_date)
    inst_ids = [m["instrument"].id for m in all_members]
    if not inst_ids:
        all_insts = list(db.scalars(select(Instrument).where(Instrument.is_active == True)).all())
        inst_ids = [i.id for i in all_insts]
    portal.preload(inst_ids)

    inst_lookup = {inst_id: portal.get_instrument(inst_id) for inst_id in inst_ids}

    counts = FunnelCounts()
    rejection_reasons: dict[str, int] = {}
    captured_signals: list[dict[str, Any]] = []

    portfolio = Portfolio(initial_capital=Decimal("1000000.00"))
    simulator = ExecutionSimulator(IndianEquityDeliveryCostModel(), FixedBasisPointSlippage(bps=5))
    risk_hook = BasicCapitalGuard()

    pending_entry_orders: list[OrderIntent] = []
    pending_exit_signals: list[ExitSignal] = []

    for current_date in clock:
        portal.set_current_date(current_date)

        # 1. Process Pending Orders from session T-1 at session T Open
        # Exits
        pending_exit_signals.clear()

        # Entries
        for order in list(pending_entry_orders):
            counts.orders_scheduled_t1 += 1
            bar = portal.get_bar(order.instrument_id, current_date)
            if bar:
                counts.fill_attempts += 1
                exec_res = simulator.simulate_entry_execution(order, bar, current_date, portfolio.cash)
                if exec_res.filled:
                    counts.successful_fills += 1
                    counts.positions_opened += 1
                    pos = portfolio.process_entry_fill(exec_res, "UNKNOWN")
                else:
                    reason = exec_res.rejection_reason or "UNKNOWN_REJECTION"
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                    if "trace_item" in order.metadata:
                        order.metadata["trace_item"]["execution_fill_attempted"] = True
                        order.metadata["trace_item"]["execution_filled"] = False
                        order.metadata["trace_item"]["execution_rejection_reason"] = reason

        pending_entry_orders.clear()

        # 2. Strategy Evaluation at session T Close
        univ_members = portal.get_universe_members(current_date)
        counts.eligible_observations += len(univ_members)

        signals = strategy.evaluate(current_date, portal)
        counts.confirmed_signals += len(signals)

        for sig in signals:
            if isinstance(sig, SignalIntent):
                counts.signal_intent_objects += 1
                counts.risk_sizing_evaluations += 1

                inst_obj = inst_lookup.get(sig.instrument_id)
                sym = inst_obj.symbol if inst_obj else str(sig.instrument_id)

                trace_item = {
                    "family": strategy.name,
                    "instrument_id": str(sig.instrument_id),
                    "symbol": sym,
                    "signal_date": current_date.isoformat(),
                    "features": sig.metadata,
                    "signal_intent_created": True,
                    "direction": sig.direction,
                    "order_type": sig.order_type,
                    "stop_loss_level": float(sig.stop_loss_level) if sig.stop_loss_level else None,
                    "quantity_hint": sig.quantity_hint,
                    "risk_hook_accepted": False,
                    "risk_hook_rejection_reason": "",
                    "t1_date": None,
                    "t1_open": None,
                    "t1_high": None,
                    "t1_low": None,
                    "t1_close": None,
                    "execution_fill_attempted": False,
                    "execution_filled": False,
                    "execution_rejection_reason": "",
                    "final_trade_completed": False,
                }
                captured_signals.append(trace_item)

                order_obj = OrderIntent(
                    order_id=sig.instrument_id,
                    strategy_id=strategy.strategy_id,
                    strategy_version=strategy.version,
                    instrument_id=sig.instrument_id,
                    direction=sig.direction,
                    order_type=sig.order_type,
                    signal_date=current_date,
                    limit_price=sig.limit_price,
                    stop_trigger=sig.stop_trigger,
                    stop_loss_level=sig.stop_loss_level,
                    target_level=sig.target_level,
                    quantity_hint=sig.quantity_hint,
                    rationale=sig.rationale,
                    metadata={"trace_item": trace_item},
                )
                counts.orders_constructed += 1

                filtered_order = risk_hook.filter_order(order_obj, portfolio)
                if filtered_order:
                    counts.accepted_intents += 1
                    trace_item["risk_hook_accepted"] = True
                    pending_entry_orders.append(filtered_order)
                else:
                    reason = "RISK_HOOK_REJECTED"
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                    trace_item["risk_hook_rejection_reason"] = reason

    # Select representative 9 traces (3 earliest, 3 middle, 3 latest)
    selected_traces: list[SignalTraceRecord] = []
    if captured_signals:
        total_s = len(captured_signals)
        earliest_3 = captured_signals[:min(3, total_s)]
        mid_idx = total_s // 2
        middle_3 = captured_signals[max(0, mid_idx - 1):min(total_s, mid_idx + 2)][:3]
        latest_3 = captured_signals[max(0, total_s - 3):]

        combined = earliest_3 + middle_3 + latest_3
        # Deduplicate while preserving order
        seen_keys = set()
        for item in combined:
            key = (item["instrument_id"], item["signal_date"])
            if key not in seen_keys:
                seen_keys.add(key)
                selected_traces.append(SignalTraceRecord(**item))

    return counts, rejection_reasons, selected_traces


def main() -> None:
    logger.info("=== M3B.2.1 12-STAGE PIPELINE FUNNEL & SIGNAL TRACING AUDIT ===")

    v2_strats = [
        TrendPullbackV2Strategy(),
        BreakoutConfirmV2Strategy(),
        MomentumRSV2Strategy(),
        MeanReversionV2Strategy(),
    ]

    all_funnels: dict[str, Any] = {}
    all_rejections: dict[str, Any] = {}
    all_traces: list[dict[str, Any]] = []

    with SessionLocal() as db:
        for strat in v2_strats:
            logger.info(f"\nAuditing family: {strat.name} ({strat.strategy_id})...")
            counts, rejections, traces = audit_strategy_family(db, strat)

            logger.info(f"   Eligible Obs: {counts.eligible_observations}")
            logger.info(f"   Confirmed Signals: {counts.confirmed_signals}")
            logger.info(f"   SignalIntent Objects: {counts.signal_intent_objects}")
            logger.info(f"   Risk/Sizing Evaluations: {counts.risk_sizing_evaluations}")
            logger.info(f"   Accepted Intents: {counts.accepted_intents}")
            logger.info(f"   Orders Constructed: {counts.orders_constructed}")
            logger.info(f"   Orders Scheduled T+1: {counts.orders_scheduled_t1}")
            logger.info(f"   Fill Attempts: {counts.fill_attempts}")
            logger.info(f"   Successful Fills: {counts.successful_fills}")
            logger.info(f"   Positions Opened: {counts.positions_opened}")
            logger.info(f"   Completed Trades: {counts.completed_trades}")
            logger.info(f"   Rejection Reasons: {rejections}")

            # Identify PRIMARY_ZERO_DROP_BOUNDARY
            stages = [
                ("ELIGIBLE_OBSERVATIONS", counts.eligible_observations),
                ("CONFIRMED_SIGNALS", counts.confirmed_signals),
                ("SIGNAL_INTENT_OBJECTS", counts.signal_intent_objects),
                ("RISK_SIZING_EVALUATIONS", counts.risk_sizing_evaluations),
                ("ACCEPTED_INTENTS", counts.accepted_intents),
                ("ORDERS_CONSTRUCTED", counts.orders_constructed),
                ("ORDERS_SCHEDULED_T1", counts.orders_scheduled_t1),
                ("FILL_ATTEMPTS", counts.fill_attempts),
                ("SUCCESSFUL_FILLS", counts.successful_fills),
                ("POSITIONS_OPENED", counts.positions_opened),
                ("COMPLETED_TRADES", counts.completed_trades),
            ]

            zero_boundary = "NONE"
            for i in range(len(stages) - 1):
                curr_n, curr_c = stages[i]
                next_n, next_c = stages[i + 1]
                if curr_c > 0 and next_c == 0:
                    zero_boundary = f"{curr_n}_TO_{next_n}"
                    break

            logger.info(f"   PRIMARY ZERO DROP BOUNDARY: {zero_boundary}")

            all_funnels[strat.strategy_id] = asdict(counts)
            all_funnels[strat.strategy_id]["zero_boundary"] = zero_boundary
            all_rejections[strat.strategy_id] = rejections
            for t in traces:
                all_traces.append(asdict(t))

    # Export audit results
    audit_summary = {
        "funnel_counts": all_funnels,
        "rejection_reasons": all_rejections,
        "traces": all_traces,
    }

    with open("scratch/m3b_2_1_pipeline_audit_results.json", "w") as f:
        json.dump(audit_summary, f, indent=2)

    logger.info("\nPipeline audit complete. Results saved to scratch/m3b_2_1_pipeline_audit_results.json")


if __name__ == "__main__":
    main()
