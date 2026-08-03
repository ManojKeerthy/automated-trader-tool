"""Top-level Backtest Engine Orchestrator.

Integrates HistoricalClock, DataPortal, ExecutionSimulator, Portfolio,
TradeLedger, RiskHooks, CostModel, SlippageModel, and MetricsEngine.

Enforces:
- Research quality classification (TRUSTWORTHY, RESEARCH_ONLY, UNVERIFIED, BLOCKED)
- Survivorship bias gating
- Corporate action quality gating
- Signal timing (T -> T+1 execution)
- Deterministic reproducible results
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tradecraft.backtesting.benchmark import Benchmark, BenchmarkResult
from tradecraft.backtesting.clock import HistoricalClock
from tradecraft.backtesting.costs import CostBreakdown, CostModel, IndianEquityDeliveryCostModel
from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.backtesting.execution import ExecutionSimulator, OrderIntent
from tradecraft.backtesting.metrics import BacktestMetricsSummary, MetricsEngine
from tradecraft.backtesting.portfolio import EquitySnapshot, Portfolio
from tradecraft.backtesting.risk_hooks import BasicCapitalGuard, RiskHook
from tradecraft.backtesting.slippage import FixedBasisPointSlippage, SlippageModel
from tradecraft.backtesting.trade_ledger import TradeLedger, TradeRecord
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.research.risk_free_rate import RiskFreeRateConfig
from tradecraft.research.sizing import ResearchSizingCalculator
from tradecraft.strategy.base import ExitSignal, SignalIntent, Strategy

logger = logging.getLogger(__name__)

# Research Quality Classifications per approved amendments
TRUSTWORTHY = "TRUSTWORTHY"
RESEARCH_ONLY = "RESEARCH_ONLY"
UNVERIFIED = "UNVERIFIED"
BLOCKED = "BLOCKED"


class EndOfBacktestPolicy(Enum):
    """Policy for handling open positions when a backtest window reaches end_date."""

    MARK_TO_MARKET = "MARK_TO_MARKET"
    FORCE_CLOSE = "FORCE_CLOSE"


@dataclass
class BacktestConfig:
    """Configuration parameters for a backtest run."""

    strategy: Strategy
    universe_name: str = "NIFTY_50"
    start_date: date = date(2026, 1, 1)
    end_date: date = date(2026, 7, 28)
    initial_capital: Decimal = Decimal("50000.00")
    cost_model: CostModel = field(default_factory=IndianEquityDeliveryCostModel)
    slippage_model: SlippageModel = field(default_factory=FixedBasisPointSlippage)
    benchmark: Benchmark = field(default_factory=Benchmark)
    risk_free_config: RiskFreeRateConfig = field(default_factory=RiskFreeRateConfig)
    risk_hook: RiskHook = field(default_factory=BasicCapitalGuard)
    allow_unverified_universe: bool = True  # If True, classifies run as UNVERIFIED/RESEARCH_ONLY
    end_of_backtest_policy: EndOfBacktestPolicy = EndOfBacktestPolicy.MARK_TO_MARKET


@dataclass
class BacktestResult:
    """Complete result bundle from a backtest execution."""

    run_id: uuid.UUID
    config: BacktestConfig
    research_quality: str  # TRUSTWORTHY, RESEARCH_ONLY, UNVERIFIED, BLOCKED
    warnings: list[str]
    equity_curve: list[EquitySnapshot]
    trades: list[TradeRecord]
    metrics: BacktestMetricsSummary
    benchmark_result: BenchmarkResult | None


class BacktestEngine:
    """Deterministic EOD backtest engine orchestrator."""

    def __init__(
        self,
        db_session: Session,
        calendar_instance: Any,
    ):
        self.db = db_session
        self.calendar = calendar_instance

    def run(self, config: BacktestConfig) -> BacktestResult:
        """Execute the backtest deterministically."""
        run_id = uuid.uuid4()
        warnings: list[str] = []

        logger.info(
            f"Starting backtest run {run_id} for strategy {config.strategy.name}-v{config.strategy.version}"
        )

        # 1. Setup Universe & Research Quality Classification
        pit_universe = PointInTimeUniverse(self.db, index_name=config.universe_name)
        universe_confidence = pit_universe.membership_confidence(config.start_date)

        research_quality = TRUSTWORTHY

        if universe_confidence != "VERIFIED":
            warnings.append(
                f"Universe membership for {config.universe_name} is UNVERIFIED. "
                "Backtest carries potential survivorship bias."
            )
            research_quality = UNVERIFIED if config.allow_unverified_universe else BLOCKED

        if config.cost_model.is_historical_assumption:
            warnings.append(
                f"Cost model {config.cost_model.version} contains COST_MODEL_HISTORICAL_ASSUMPTION."
            )

        profile_name = getattr(config.cost_model, "profile_name", "standard")
        warnings.append(f"Cost model DP profile assumption: {profile_name}")

        if research_quality == BLOCKED:
            raise ValueError(f"Backtest blocked due to research quality policy: {warnings}")

        # 2. Setup Clock and DataPortal
        clock = HistoricalClock(self.calendar, config.start_date, config.end_date)
        portal = DataPortal(self.db, pit_universe, config.start_date, config.end_date)

        # Identify all instruments present in the backtest window
        all_members = pit_universe.members(config.start_date)
        inst_ids = [m["instrument"].id for m in all_members]
        if not inst_ids:
            # Fallback: get all active instruments from DB if universe table is empty
            from tradecraft.core.db_models import Instrument

            all_insts = list(
                self.db.scalars(
                    select(Instrument).where(Instrument.is_active == True)  # noqa: E712
                ).all()
            )
            inst_ids = [i.id for i in all_insts]
            # Seed unverified universe
            pit_universe.seed_current_members(all_insts)

        portal.preload(inst_ids)

        # 3. Setup Portfolio, Simulator, Ledger & Sizer
        portfolio = Portfolio(initial_capital=config.initial_capital)
        simulator = ExecutionSimulator(config.cost_model, config.slippage_model)
        ledger = TradeLedger(run_id)
        sizing_calculator = ResearchSizingCalculator(allocation_pct=Decimal("0.10"))

        # Queued order intents for session T+1 execution
        pending_entry_orders: list[OrderIntent] = []
        pending_exit_signals: list[ExitSignal] = []

        # Track daily sold instruments for DP charge de-duplication: set of (date, instrument_id)
        daily_sold_instruments: set[tuple[date, uuid.UUID]] = set()

        # 4. Chronological Simulation Loop
        for current_date in clock:
            portal.set_current_date(current_date)

            # A. Process Pending Orders from session T-1 at session T Open
            # -----------------------------------------------------------
            # Process Exits first
            for exit_sig in list(pending_exit_signals):
                if exit_sig.instrument_id in portfolio.positions:
                    pos = portfolio.positions[exit_sig.instrument_id]
                    bar = portal.get_bar(pos.instrument_id, current_date)
                    if bar:
                        is_first_sell = (current_date, pos.instrument_id) not in daily_sold_instruments
                        exec_res = simulator.simulate_exit_execution(
                            position_id=pos.position_id,
                            strategy_id=pos.strategy_id,
                            strategy_version=pos.strategy_version,
                            instrument_id=pos.instrument_id,
                            quantity=pos.quantity,
                            stop_loss_level=pos.current_stop,
                            target_level=pos.current_target,
                            exit_signal=exit_sig,
                            bar=bar,
                            execution_date=current_date,
                            is_first_isin_sell_today=is_first_sell,
                        )
                        if exec_res and exec_res.filled:
                            daily_sold_instruments.add((current_date, pos.instrument_id))
                            sig_dt = pos.signal_date or pos.entry_date
                            entry_costs = pos.entry_costs_breakdown or CostBreakdown()

                            # Record in ledger
                            ledger.record_trade(
                                instrument_id=pos.instrument_id,
                                symbol=pos.symbol,
                                strategy_name=pos.strategy_id,
                                strategy_version=pos.strategy_version,
                                signal_date=sig_dt,
                                entry_date=pos.entry_date,
                                entry_price=pos.avg_entry_price,
                                exit_date=current_date,
                                exit_price=exec_res.fill_price,  # type: ignore
                                quantity=exec_res.quantity,
                                entry_costs=entry_costs,
                                exit_costs=exec_res.costs,
                                slippage_cost=exec_res.slippage_cost,
                                exit_reason=exec_res.exit_reason or "STRATEGY_SIGNAL",
                            )

                            portfolio.process_exit_fill(exec_res)
                            if exec_res.is_ambiguous_bar:
                                warnings.append(
                                    f"OHLC ambiguity on {current_date} for {pos.symbol}: "
                                    "Both stop-loss & target were touched on same bar. Assumed stop-loss."
                                )

            pending_exit_signals.clear()

            # Check protective stops/targets for existing positions not manually exited
            for inst_id, pos in list(portfolio.positions.items()):
                bar = portal.get_bar(inst_id, current_date)
                if bar and (pos.current_stop or pos.current_target):
                    is_first_sell = (current_date, pos.instrument_id) not in daily_sold_instruments
                    exec_res = simulator.simulate_exit_execution(
                        position_id=pos.position_id,
                        strategy_id=pos.strategy_id,
                        strategy_version=pos.strategy_version,
                        instrument_id=pos.instrument_id,
                        quantity=pos.quantity,
                        stop_loss_level=pos.current_stop,
                        target_level=pos.current_target,
                        exit_signal=None,
                        bar=bar,
                        execution_date=current_date,
                        is_first_isin_sell_today=is_first_sell,
                    )
                    if exec_res and exec_res.filled:
                        daily_sold_instruments.add((current_date, pos.instrument_id))
                        sig_dt = pos.signal_date or pos.entry_date
                        entry_costs = pos.entry_costs_breakdown or CostBreakdown()

                        ledger.record_trade(
                            instrument_id=pos.instrument_id,
                            symbol=pos.symbol,
                            strategy_name=pos.strategy_id,
                            strategy_version=pos.strategy_version,
                            signal_date=sig_dt,
                            entry_date=pos.entry_date,
                            entry_price=pos.avg_entry_price,
                            exit_date=current_date,
                            exit_price=exec_res.fill_price,  # type: ignore
                            quantity=exec_res.quantity,
                            entry_costs=entry_costs,
                            exit_costs=exec_res.costs,
                            slippage_cost=exec_res.slippage_cost,
                            exit_reason=exec_res.exit_reason or "PROTECTIVE_EXIT",
                            stop_loss_level=pos.current_stop,
                        )
                        portfolio.process_exit_fill(exec_res)
                        if exec_res.is_ambiguous_bar:
                            warnings.append(
                                f"OHLC ambiguity on {current_date} for {pos.symbol}: "
                                "Both stop-loss & target were touched on same bar. Assumed stop-loss."
                            )

            # Process Entries
            for order in list(pending_entry_orders):
                bar = portal.get_bar(order.instrument_id, current_date)
                if bar:
                    # Resolve unsized orders using approved ResearchSizingCalculator (10% allocation)
                    if order.quantity_hint is None or order.quantity_hint <= 0:
                        est_fill = simulator.slippage_model.apply(bar["open"], order.direction, 0)
                        size_res = sizing_calculator.calculate_quantity(
                            portfolio.total_equity, portfolio.cash, est_fill
                        )
                        if size_res.is_valid and size_res.quantity >= 1:
                            order.quantity_hint = size_res.quantity

                    # Apply risk hook
                    filtered_order = config.risk_hook.filter_order(order, portfolio)
                    if filtered_order:
                        inst = portal.get_instrument(order.instrument_id)
                        sym = inst.symbol if inst else "UNKNOWN"
                        exec_res = simulator.simulate_entry_execution(
                            filtered_order, bar, current_date, portfolio.cash
                        )
                        if exec_res.filled:
                            pos = portfolio.process_entry_fill(exec_res, sym, signal_date=order.signal_date)

            pending_entry_orders.clear()

            # B. Mark Portfolio to Market at session T Close
            # ----------------------------------------------
            closing_prices: dict[uuid.UUID, Decimal] = {}
            for inst_id in portfolio.positions:
                c_price = portal.get_close(inst_id, current_date)
                if c_price:
                    closing_prices[inst_id] = c_price

            portfolio.mark_to_market(current_date, closing_prices)

            # C. Strategy Evaluation at session T Close
            # -----------------------------------------
            signals = config.strategy.evaluate(current_date, portal)

            for sig in signals:
                if isinstance(sig, SignalIntent):
                    pending_entry_orders.append(
                        OrderIntent(
                            order_id=uuid.uuid4(),
                            strategy_id=config.strategy.strategy_id,
                            strategy_version=config.strategy.version,
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
                            metadata=sig.metadata,
                        )
                    )
                elif isinstance(sig, ExitSignal):
                    pending_exit_signals.append(sig)

        # 4.5. Process EndOfBacktestPolicy.FORCE_CLOSE if configured
        if config.end_of_backtest_policy == EndOfBacktestPolicy.FORCE_CLOSE and portfolio.positions:
            final_date = config.end_date
            for inst_id, pos in list(portfolio.positions.items()):
                bar = portal.get_bar(inst_id, final_date)
                if bar:
                    is_first_sell = (final_date, pos.instrument_id) not in daily_sold_instruments
                    force_exit_sig = ExitSignal(
                        instrument_id=pos.instrument_id,
                        reason="END_OF_BACKTEST",
                    )
                    exec_res = simulator.simulate_exit_execution(
                        position_id=pos.position_id,
                        strategy_id=pos.strategy_id,
                        strategy_version=pos.strategy_version,
                        instrument_id=pos.instrument_id,
                        quantity=pos.quantity,
                        stop_loss_level=pos.current_stop,
                        target_level=pos.current_target,
                        exit_signal=force_exit_sig,
                        bar=bar,
                        execution_date=final_date,
                        is_first_isin_sell_today=is_first_sell,
                    )
                    if exec_res and exec_res.filled:
                        daily_sold_instruments.add((final_date, pos.instrument_id))
                        sig_dt = pos.signal_date or pos.entry_date
                        entry_costs = pos.entry_costs_breakdown or CostBreakdown()

                        ledger.record_trade(
                            instrument_id=pos.instrument_id,
                            symbol=pos.symbol,
                            strategy_name=pos.strategy_id,
                            strategy_version=pos.strategy_version,
                            signal_date=sig_dt,
                            entry_date=pos.entry_date,
                            entry_price=pos.avg_entry_price,
                            exit_date=final_date,
                            exit_price=exec_res.fill_price,  # type: ignore
                            quantity=exec_res.quantity,
                            entry_costs=entry_costs,
                            exit_costs=exec_res.costs,
                            slippage_cost=exec_res.slippage_cost,
                            exit_reason="END_OF_BACKTEST",
                        )
                        portfolio.process_exit_fill(exec_res)
            # Re-record final equity snapshot with zero open positions and updated cash
            portfolio.mark_to_market(final_date, {})

        # 5. Compute Validation Metrics
        metrics_engine = MetricsEngine(config.risk_free_config)
        metrics_summary = metrics_engine.calculate(
            equity_curve=portfolio.equity_curve,
            trades=ledger.trades,
            initial_capital=config.initial_capital,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        # 6. Evaluate Benchmark
        benchmark_res = config.benchmark.calculate_return(
            config.start_date, config.end_date, portal
        )

        logger.info(
            f"Backtest run {run_id} complete. Total return: {metrics_summary.metrics.get('total_return_pct')}"
        )

        return BacktestResult(
            run_id=run_id,
            config=config,
            research_quality=research_quality,
            warnings=warnings,
            equity_curve=portfolio.equity_curve,
            trades=ledger.trades,
            metrics=metrics_summary,
            benchmark_result=benchmark_res,
        )
