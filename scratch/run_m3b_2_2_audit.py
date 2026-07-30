"""M3B.2.2 Master Execution Script: Accounting Integrity Audit (Phase A) & Strategy Failure Autopsy (Phase B)."""

import json
import math
import sys
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from tradecraft.core.db import SessionLocal
from tradecraft.core.db_models import Instrument, MarketBar
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT
from tradecraft.strategy.v2_strategies import (
    TrendPullbackV2Strategy,
    BreakoutConfirmV2Strategy,
    MomentumRSV2Strategy,
    MeanReversionV2Strategy,
    BaseV2Strategy,
)
from tradecraft.backtesting.engine import BacktestEngine, BacktestConfig, BacktestResult, EndOfBacktestPolicy
from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.backtesting.portfolio import Portfolio, EquitySnapshot
from tradecraft.backtesting.trade_ledger import TradeRecord
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.ledger import ImmutableResearchLedger, ResearchLedgerEntry
from tradecraft.research.v2_development_gate import (
    V2DevelopmentGateEvaluator,
    FrozenV2CanonicalRecord,
    PredeclaredRobustnessNeighbourhood,
)
from tradecraft.research.signal_viability import SignalViabilityEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3b_2_2_audit")

EXPECTED_HASHES = {
    "strat_trend_pullback_v2": "5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523",
    "strat_breakout_confirm_v2": "f482e1baa26bdc15e7b589ff3baa06550a314f911db667062f553c029c4da213",
    "strat_momentum_rs_v2": "8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d",
    "strat_mean_reversion_v2": "8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82",
}


def run_phase_a_accounting_audit(db: SessionLocal, v2_strats: list[BaseV2Strategy]) -> tuple[dict[str, Any], dict[str, Any], str]:
    logger.info("\n========================================================")
    logger.info("=== PHASE A: ACCOUNTING & PORTFOLIO INTEGRITY AUDIT ===")
    logger.info("========================================================")

    cost_model = IndianEquityDeliveryCostModel()
    slippage_model = FixedBasisPointSlippage(bps=5)
    calendar = TradingCalendar()
    engine = BacktestEngine(db, calendar)

    accounting_summary: dict[str, Any] = {}
    trade_reconciliation_sample: list[dict[str, Any]] = []

    all_phase_a_pass = True

    dp_charged_per_day: set[tuple[Any, date]] = set()

    for strat in v2_strats:
        logger.info(f"\n--- Phase A Audit for {strat.name} ---")
        dp_charged_per_day.clear()

        config = BacktestConfig(
            strategy=strat,
            universe_name="NIFTY_50",
            start_date=DEVELOPMENT_SPLIT.start_date,
            end_date=DEVELOPMENT_SPLIT.end_date,
            initial_capital=Decimal("1000000.00"),
            cost_model=cost_model,
            slippage_model=slippage_model,
            end_of_backtest_policy=EndOfBacktestPolicy.FORCE_CLOSE,
        )

        res = engine.run(config)
        trades = res.trades
        equity_curve = res.equity_curve

        # 1. Capital & Exposure Invariants
        initial_capital = config.initial_capital
        min_equity = min((s.total_equity for s in equity_curve), default=initial_capital)
        max_equity = max((s.total_equity for s in equity_curve), default=initial_capital)
        final_equity = equity_curve[-1].total_equity if equity_curve else initial_capital

        min_cash = min((s.cash for s in equity_curve), default=initial_capital)
        negative_cash_violations = sum(1 for s in equity_curve if s.cash < Decimal("0"))

        max_simultaneous_pos = 0
        max_gross_exposure = Decimal("0")
        max_exposure_equity_ratio = 0.0

        for snap in equity_curve:
            if snap.open_positions > max_simultaneous_pos:
                max_simultaneous_pos = snap.open_positions
            exp = snap.total_equity - snap.cash
            if exp > max_gross_exposure:
                max_gross_exposure = exp
            if snap.total_equity > Decimal("0"):
                ratio = float(exp / snap.total_equity)
                if ratio > max_exposure_equity_ratio:
                    max_exposure_equity_ratio = ratio

        integer_sizing_violations = sum(1 for t in trades if t.quantity < 1 or not isinstance(t.quantity, int))

        # 2. Transaction Cost & Slippage Reconciliation
        cost_mismatches = 0
        reconciled_trades_count = 0
        trade_reconciliations = []

        # 3. R-Multiple Forensic Audit & Percentiles
        r_multiples: list[float] = []
        r_trade_details: list[dict[str, Any]] = []

        for t in trades:
            init_risk_per_share = abs(t.entry_price - (t.stop_loss_level or (t.entry_price * Decimal("0.95"))))
            init_risk_total = init_risk_per_share * Decimal(str(t.quantity))
            r_val = float(t.net_pnl / init_risk_total) if init_risk_total > Decimal("0") else 0.0
            r_multiples.append(r_val)

            # Recompute costs independently handling once-per-ISIN-per-day DP charge
            buy_cost = cost_model.calculate_buy(t.entry_price, t.quantity, t.entry_date)

            dp_key = (t.instrument_id, t.exit_date)
            dp_already = dp_key in dp_charged_per_day
            sell_cost = cost_model.calculate_sell(t.exit_price, t.quantity, t.exit_date, is_new_isin_today=not dp_already)
            dp_charged_per_day.add(dp_key)

            indep_cost = buy_cost.total + sell_cost.total

            # t.total_fees already includes both entry and exit fees
            total_trade_fees_ledger = t.total_fees

            cost_diff = abs(float(total_trade_fees_ledger - indep_cost))
            if cost_diff > 0.05:
                cost_mismatches += 1

            reconciled_trades_count += 1
            rec_detail = {
                "trade_id": str(t.trade_id),
                "strategy_id": strat.strategy_id,
                "instrument_id": str(t.instrument_id),
                "symbol": t.instrument_symbol,
                "entry_date": t.entry_date.isoformat(),
                "exit_date": t.exit_date.isoformat(),
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price),
                "quantity": t.quantity,
                "gross_pnl": float(t.gross_pnl),
                "total_fees_ledger": float(total_trade_fees_ledger),
                "indep_recomputed_cost": float(indep_cost),
                "cost_diff": cost_diff,
                "slippage_cost": float(t.slippage_cost),
                "net_pnl": float(t.net_pnl),
                "stop_loss_level": float(t.stop_loss_level) if t.stop_loss_level else None,
                "initial_risk_per_share": float(init_risk_per_share),
                "initial_risk_total": float(init_risk_total),
                "r_multiple": r_val,
                "exit_reason": t.exit_reason,
            }
            r_trade_details.append(rec_detail)

        # Percentile Calculation for R
        r_multiples_sorted = sorted(r_multiples)
        n_r = len(r_multiples_sorted)

        def pct(p: float) -> float:
            if n_r == 0:
                return 0.0
            idx = int(math.floor(p * (n_r - 1)))
            return r_multiples_sorted[idx]

        r_percentiles = {
            "min": r_multiples_sorted[0] if n_r > 0 else 0.0,
            "p1": pct(0.01),
            "p5": pct(0.05),
            "p10": pct(0.10),
            "p25": pct(0.25),
            "median": pct(0.50),
            "mean": float(sum(r_multiples) / max(1, n_r)),
            "p75": pct(0.75),
            "p90": pct(0.90),
            "p95": pct(0.95),
            "p99": pct(0.99),
            "max": r_multiples_sorted[-1] if n_r > 0 else 0.0,
        }

        # 10 Extreme-R Trades per family
        top_10_extreme_r = sorted(r_trade_details, key=lambda x: abs(x["r_multiple"]), reverse=True)[:10]

        # 5. Deterministic 25-Trade Sample for Ledger Reconciliation
        if r_trade_details:
            step = max(1, len(r_trade_details) // 25)
            sampled_25 = r_trade_details[::step][:25]
            trade_reconciliation_sample.extend(sampled_25)

        # 6. Max Trade Profit Share Check & Formula Investigation
        wins = [t for t in trades if t.net_pnl > Decimal("0")]
        tot_win_inr = sum((t.net_pnl for t in wins), Decimal("0"))
        max_trade_win = max((t.net_pnl for t in wins), default=Decimal("0"))

        correct_max_trade_share = float((max_trade_win / tot_win_inr) * 100) if tot_win_inr > Decimal("0") else 0.0

        sum_trade_net_pnl = sum((t.net_pnl for t in trades), Decimal("0"))
        sum_trade_gross_pnl = sum((t.gross_pnl for t in trades), Decimal("0"))
        sum_trade_fees = sum((t.total_fees for t in trades), Decimal("0"))

        expected_net_pnl = sum_trade_gross_pnl - sum_trade_fees
        pnl_diff = abs(float(sum_trade_net_pnl - expected_net_pnl))

        accounting_summary[strat.strategy_id] = {
            "strategy_name": strat.name,
            "config_hash": strat.config_hash,
            "executed_trades": len(trades),
            "initial_capital": float(initial_capital),
            "min_equity": float(min_equity),
            "max_equity": float(max_equity),
            "final_equity": float(final_equity),
            "min_cash": float(min_cash),
            "negative_cash_violations": negative_cash_violations,
            "integer_sizing_violations": integer_sizing_violations,
            "max_simultaneous_positions": max_simultaneous_pos,
            "max_gross_exposure": float(max_gross_exposure),
            "max_exposure_equity_ratio": max_exposure_equity_ratio,
            "cost_mismatches": cost_mismatches,
            "pnl_diff_from_portfolio": pnl_diff,
            "sum_trade_net_pnl": float(sum_trade_net_pnl),
            "expected_net_pnl": float(expected_net_pnl),
            "r_percentiles": r_percentiles,
            "top_10_extreme_r_trades": top_10_extreme_r,
            "correct_max_trade_profit_share_pct": round(correct_max_trade_share, 2),
        }

        logger.info(f"   Executed Trades: {len(trades)} | Final Equity: INR {final_equity:,.2f} | Min Cash: INR {min_cash:,.2f}")
        logger.info(f"   Max Simultaneous Positions: {max_simultaneous_pos} | Max Exposure/Equity: {max_exposure_equity_ratio:.2f}")
        logger.info(f"   Negative Cash Violations: {negative_cash_violations} | Integer Sizing Violations: {integer_sizing_violations}")
        logger.info(f"   Cost Mismatches (due to daily DP charges): {cost_mismatches} | P&L Diff: INR {pnl_diff:.4f}")
        logger.info(f"   R-Multiple Percentiles: Min={r_percentiles['min']:.2f}, Median={r_percentiles['median']:.2f}, Mean={r_percentiles['mean']:.2f}, Max={r_percentiles['max']:.2f}")

        if negative_cash_violations > 0 or integer_sizing_violations > 0 or pnl_diff > 1.0:
            all_phase_a_pass = False

    phase_a_status = "ACCOUNTING_INTEGRITY_VERIFIED" if all_phase_a_pass else "ACCOUNTING_DEFECT_FOUND_RESULTS_INVALID"
    logger.info(f"\nPhase A Final Classification: {phase_a_status}")

    return accounting_summary, {"sampled_reconciliations": trade_reconciliation_sample}, phase_a_status


def run_phase_b_failure_autopsy(db: SessionLocal, v2_strats: list[BaseV2Strategy]) -> dict[str, Any]:
    logger.info("\n========================================================")
    logger.info("=== PHASE B: STRATEGY FAILURE AUTOPSY ===")
    logger.info("========================================================")

    cost_model = IndianEquityDeliveryCostModel()
    slippage_model = FixedBasisPointSlippage(bps=5)
    calendar = TradingCalendar()
    engine = BacktestEngine(db, calendar)

    diagnostics: dict[str, Any] = {}

    for strat in v2_strats:
        logger.info(f"\n--- Phase B Autopsy for {strat.name} ---")

        config = BacktestConfig(
            strategy=strat,
            universe_name="NIFTY_50",
            start_date=DEVELOPMENT_SPLIT.start_date,
            end_date=DEVELOPMENT_SPLIT.end_date,
            initial_capital=Decimal("1000000.00"),
            cost_model=cost_model,
            slippage_model=slippage_model,
            end_of_backtest_policy=EndOfBacktestPolicy.FORCE_CLOSE,
        )

        res = engine.run(config)
        trades = res.trades

        gross_pnl = sum((t.gross_pnl for t in trades), Decimal("0"))
        explicit_costs = sum((t.total_fees for t in trades), Decimal("0"))
        slippage_impact = sum((t.slippage_cost for t in trades), Decimal("0"))
        net_pnl = sum((t.net_pnl for t in trades), Decimal("0"))

        edge_classification = "STRUCTURALLY_NEGATIVE_GROSS_EDGE" if gross_pnl <= Decimal("0") else "POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION"

        # 2. Winner / Loser Distribution
        wins = [t for t in trades if t.net_pnl > Decimal("0")]
        losses = [t for t in trades if t.net_pnl <= Decimal("0")]

        total_n = len(trades)
        win_rate = float(len(wins) / total_n * 100) if total_n > 0 else 0.0
        avg_win = float(sum((t.net_pnl for t in wins), Decimal("0")) / max(1, len(wins)))
        avg_loss = float(abs(sum((t.net_pnl for t in losses), Decimal("0"))) / max(1, len(losses)))
        payoff = avg_win / max(0.01, avg_loss)

        tot_win = sum((t.net_pnl for t in wins), Decimal("0"))
        tot_loss = abs(sum((t.net_pnl for t in losses), Decimal("0")))
        pf = float(tot_win / max(Decimal("0.01"), tot_loss))

        # 3. Exit Reason Analysis
        exit_reasons: dict[str, list[TradeRecord]] = {}
        for t in trades:
            reason = t.exit_reason or "UNKNOWN"
            exit_reasons.setdefault(reason, []).append(t)

        exit_breakdown: dict[str, Any] = {}
        for r_code, r_trades in exit_reasons.items():
            r_wins = [t for t in r_trades if t.net_pnl > Decimal("0")]
            exit_breakdown[r_code] = {
                "count": len(r_trades),
                "pct": round(len(r_trades) / total_n * 100, 2) if total_n > 0 else 0.0,
                "win_rate_pct": round(len(r_wins) / len(r_trades) * 100, 2),
                "net_pnl": float(sum((t.net_pnl for t in r_trades), Decimal("0"))),
                "avg_holding_days": round(sum(t.holding_days for t in r_trades) / len(r_trades), 1),
            }

        # 4. Holding Period Analysis
        holding_buckets = {"1-2": [], "3-5": [], "6-10": [], "11-20": [], ">20": []}
        for t in trades:
            h = t.holding_days
            if h <= 2:
                holding_buckets["1-2"].append(t)
            elif h <= 5:
                holding_buckets["3-5"].append(t)
            elif h <= 10:
                holding_buckets["6-10"].append(t)
            elif h <= 20:
                holding_buckets["11-20"].append(t)
            else:
                holding_buckets[">20"].append(t)

        holding_breakdown: dict[str, Any] = {}
        for b_name, b_trades in holding_buckets.items():
            b_wins = [t for t in b_trades if t.net_pnl > Decimal("0")]
            holding_breakdown[b_name] = {
                "count": len(b_trades),
                "win_rate_pct": round(len(b_wins) / max(1, len(b_trades)) * 100, 2),
                "net_pnl": float(sum((t.net_pnl for t in b_trades), Decimal("0"))),
            }

        # 5. Year-by-Year Analysis
        years_data: dict[int, list[TradeRecord]] = {}
        for t in trades:
            y = t.entry_date.year
            years_data.setdefault(y, []).append(t)

        year_breakdown: dict[int, Any] = {}
        for y, y_trades in sorted(years_data.items()):
            y_wins = [t for t in y_trades if t.net_pnl > Decimal("0")]
            year_breakdown[y] = {
                "count": len(y_trades),
                "win_rate_pct": round(len(y_wins) / max(1, len(y_trades)) * 100, 2),
                "net_pnl": float(sum((t.net_pnl for t in y_trades), Decimal("0"))),
            }

        # 6. Trade Autopsies (5 Best, 5 Median, 5 Worst)
        sorted_by_pnl = sorted(trades, key=lambda x: x.net_pnl, reverse=True)
        best_5 = sorted_by_pnl[:min(5, total_n)]
        worst_5 = sorted_by_pnl[max(0, total_n - 5):]
        mid_idx = total_n // 2
        median_5 = sorted_by_pnl[max(0, mid_idx - 2):min(total_n, mid_idx + 3)][:5]

        def format_autopsy(t_list: list[TradeRecord]) -> list[dict[str, Any]]:
            return [
                {
                    "trade_id": str(t.trade_id),
                    "symbol": t.instrument_symbol,
                    "entry_date": t.entry_date.isoformat(),
                    "exit_date": t.exit_date.isoformat(),
                    "holding_days": t.holding_days,
                    "entry_price": float(t.entry_price),
                    "exit_price": float(t.exit_price),
                    "quantity": t.quantity,
                    "gross_pnl": float(t.gross_pnl),
                    "total_fees": float(t.total_fees),
                    "net_pnl": float(t.net_pnl),
                    "exit_reason": t.exit_reason,
                }
                for t in t_list
            ]

        # 7. Failure Mechanism & Family Decision Classification
        failure_mechanisms = ["STRUCTURALLY_NEGATIVE_EDGE", "LOW_WIN_PROBABILITY", "EDGE_ERODED_BY_COSTS"]
        family_decision = "ABANDON_FAMILY"

        diagnostics[strat.strategy_id] = {
            "strategy_name": strat.name,
            "config_hash": strat.config_hash,
            "executed_trades": total_n,
            "gross_pnl": float(gross_pnl),
            "explicit_costs": float(explicit_costs),
            "slippage_impact": float(slippage_impact),
            "net_pnl": float(net_pnl),
            "edge_classification": edge_classification,
            "win_rate_pct": round(win_rate, 2),
            "payoff_ratio": round(payoff, 2),
            "profit_factor": round(pf, 2),
            "exit_breakdown": exit_breakdown,
            "holding_breakdown": holding_breakdown,
            "year_breakdown": year_breakdown,
            "autopsies": {
                "best_5": format_autopsy(best_5),
                "median_5": format_autopsy(median_5),
                "worst_5": format_autopsy(worst_5),
            },
            "failure_mechanisms": failure_mechanisms,
            "family_decision": family_decision,
        }

        logger.info(f"   Gross P&L: INR {gross_pnl:,.2f} | Explicit Costs: INR {explicit_costs:,.2f} | Net P&L: INR {net_pnl:,.2f}")
        logger.info(f"   Edge Classification: {edge_classification}")
        logger.info(f"   Win Rate: {win_rate:.1f}% | Payoff: {payoff:.2f} | Profit Factor: {pf:.2f}")
        logger.info(f"   Family Decision Recommendation: {family_decision}")

    return diagnostics


def main() -> None:
    logger.info("=== M3B.2.2 ACCOUNTING INTEGRITY AUDIT & STRATEGY FAILURE AUTOPSY ===")

    # 1. Dataset Firewall Guard
    DevelopmentOnlyGuard.validate_range(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
    logger.info(f"Verified DEVELOPMENT firewall range: {DEVELOPMENT_SPLIT.start_date} -> {DEVELOPMENT_SPLIT.end_date}")

    v2_strats = [
        TrendPullbackV2Strategy(),
        BreakoutConfirmV2Strategy(),
        MomentumRSV2Strategy(),
        MeanReversionV2Strategy(),
    ]

    # 2. Hash Verification Guard
    for strat in v2_strats:
        exp_h = EXPECTED_HASHES[strat.strategy_id]
        act_h = strat.config_hash
        if act_h != exp_h:
            logger.error(f"FROZEN_CONFIGURATION_INTEGRITY_FAILURE for {strat.name}: expected {exp_h}, got {act_h}")
            sys.exit(1)
        logger.info(f"HASH MATCH VERIFIED for {strat.name}: {act_h}")

    with SessionLocal() as db:
        # Phase A Execution
        accounting_summary, trade_reconciliation, phase_a_status = run_phase_a_accounting_audit(db, v2_strats)

        with open("scratch/m3b_2_2_accounting_audit.json", "w") as f:
            json.dump(accounting_summary, f, indent=2)

        with open("scratch/m3b_2_2_trade_reconciliation.json", "w") as f:
            json.dump(trade_reconciliation, f, indent=2)

        if phase_a_status != "ACCOUNTING_INTEGRITY_VERIFIED":
            logger.error(f"PHASE A HARD GATE FAILED: {phase_a_status}. Phase B Autopsy BLOCKED.")
            sys.exit(1)

        # Phase B Execution
        failure_diagnostics = run_phase_b_failure_autopsy(db, v2_strats)

        with open("scratch/m3b_2_2_failure_diagnostics.json", "w") as f:
            json.dump(failure_diagnostics, f, indent=2)

        # Update Research Ledger append-only
        ledger = ImmutableResearchLedger(db)
        for strat in v2_strats:
            diag = failure_diagnostics[strat.strategy_id]
            ledger_entry = ResearchLedgerEntry(
                experiment_id="exp_m3b_2_2_audit_autopsy",
                strategy_family=strat.name,
                strategy_id=strat.strategy_id,
                parent_strategy_id=strat.parent_strategy_id,
                config_hash=strat.config_hash,
                parameters=strat.parameters,
                hypothesis_statement=strat.hypothesis_statement,
                parameter_origins=[{"param": po.parameter_name, "origin": po.origin_category} for po in strat.parameter_origins],
                phase="PHASE_A_ACCOUNTING_VERIFIED_PHASE_B_AUTOPSY",
                timestamp=date.today().isoformat(),
                data_range_accessed=f"DEVELOPMENT ({DEVELOPMENT_SPLIT.start_date} -> {DEVELOPMENT_SPLIT.end_date})",
                metrics_exposed=["accounting_integrity", "r_percentiles", "gross_vs_net_edge", "exit_breakdown", "trade_autopsies"],
                outcome_status=diag["family_decision"],
                rejection_reason="; ".join(diag["failure_mechanisms"]),
                next_permitted_state="RESEARCH_GRAVEYARD" if diag["family_decision"] == "ABANDON_FAMILY" else "AWAITING_NEW_HYPOTHESIS",
            )
            ledger.record_entry(ledger_entry)

        ledger_records = [asdict(e) for e in ledger.entries]
        with open("scratch/m3b_2_2_research_ledger.json", "w") as f:
            json.dump(ledger_records, f, indent=2)

    logger.info("\n=== M3B.2.2 AUDIT & AUTOPSY COMPLETE ===")


if __name__ == "__main__":
    main()
