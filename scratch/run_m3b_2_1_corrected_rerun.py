"""M3B.2.1 Step 4: Corrected Exact-Config DEVELOPMENT Phase D Rerun & Ledger Update."""

import json
import logging
from dataclasses import asdict
from datetime import date

from tradecraft.core.db import SessionLocal
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.ledger import ImmutableResearchLedger, ResearchLedgerEntry
from tradecraft.research.signal_viability import SignalViabilityEvaluator
from tradecraft.research.splits import DEVELOPMENT_SPLIT
from tradecraft.research.v2_development_gate import (
    FrozenV2CanonicalRecord,
    PredeclaredRobustnessNeighbourhood,
    V2DevelopmentGateEvaluator,
)
from tradecraft.strategy.v2_strategies import (
    BaseV2Strategy,
    BreakoutConfirmV2Strategy,
    MeanReversionV2Strategy,
    MomentumRSV2Strategy,
    TrendPullbackV2Strategy,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3b_2_1_rerun")


def main() -> None:
    logger.info("=== M3B.2.1 CORRECTED EXACT-CONFIG DEVELOPMENT RERUN ===")

    # 1. Dataset Firewall Guard
    DevelopmentOnlyGuard.validate_range(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
    logger.info(f"Verified DEVELOPMENT dataset firewall range: {DEVELOPMENT_SPLIT.start_date} -> {DEVELOPMENT_SPLIT.end_date}")
    logger.info("VALIDATION (2022-01-01..) and FINAL TEST (2024-07-01..) datasets are STRICTLY BLOCKED.")

    v2_strats: list[BaseV2Strategy] = [
        TrendPullbackV2Strategy(),
        BreakoutConfirmV2Strategy(),
        MomentumRSV2Strategy(),
        MeanReversionV2Strategy(),
    ]

    with SessionLocal() as db:
        ledger = ImmutableResearchLedger(db)
        evaluator = V2DevelopmentGateEvaluator(db)

        rerun_results: list[dict[str, Any]] = []

        viability_evaluator = SignalViabilityEvaluator(db)
        for strat in v2_strats:
            logger.info(f"\nEvaluating Corrected DEVELOPMENT Rerun for: {strat.name} ({strat.config_hash[:12]}...)")
            v_report = viability_evaluator.evaluate_viability(strat)

            # Create frozen record
            frozen_rec = FrozenV2CanonicalRecord(
                strategy_id=strat.strategy_id,
                strategy_name=strat.name,
                strategy_version=strat.version,
                config_hash=strat.config_hash,
                freeze_timestamp="2026-07-29T12:00:00Z",
                hypothesis_statement=strat.hypothesis_statement,
                parameters=strat.parameters,
                viability_report=v_report,
                selection_rationale="Frozen for corrected Phase D DEVELOPMENT rerun",
                robustness_neighbourhood=PredeclaredRobustnessNeighbourhood(
                    strategy_id=strat.strategy_id,
                    canonical_config_hash=strat.config_hash,
                    eligible_parameters=list(strat.parameters.keys()),
                    rationale="Predeclared parameter neighbourhood",
                    delta_map={},
                    max_configurations=5,
                    predeclared_config_hashes=[],
                ),
            )

            scorecard, trades = evaluator.evaluate_frozen_v2(frozen_rec, strat)

            logger.info(f"DEVELOPMENT Scorecard for {strat.name}:")
            logger.info(f"   Executed Trades: {scorecard.executed_trades} | Net Expectancy_R: +{scorecard.net_expectancy_r:.4f} | Net P&L: INR {scorecard.net_pnl_inr:,.2f}")
            logger.info(f"   Win Rate: {scorecard.win_rate_pct:.1f}% | Payoff: {scorecard.payoff_ratio:.2f} | Profit Factor: {scorecard.profit_factor:.2f}")
            logger.info(f"   Max Inst Profit Share: {scorecard.max_single_instrument_profit_share_pct:.1f}% | Max Trade Profit Share: {scorecard.max_single_trade_profit_share_pct:.1f}%")
            logger.info(f"   Gate Pass: {scorecard.gate_pass} | Outcome: {scorecard.outcome_status}")

            outcome = scorecard.outcome_status
            next_state = "RESEARCH_GRAVEYARD"
            if outcome == "V2_DEVELOPMENT_SURVIVOR":
                next_state = "AWAITING_VALIDATION_APPROVAL"

            # Record ledger entry marked as CORRECTED RERUN (Supersedes original Phase D run)
            ledger_entry = ResearchLedgerEntry(
                experiment_id="exp_m3b_2_1_corrected_rerun",
                strategy_family=strat.name,
                strategy_id=strat.strategy_id,
                parent_strategy_id=strat.parent_strategy_id,
                config_hash=strat.config_hash,
                parameters=strat.parameters,
                hypothesis_statement=strat.hypothesis_statement,
                parameter_origins=[{"param": po.parameter_name, "origin": po.origin_category} for po in strat.parameter_origins],
                phase="PHASE_D_DEVELOPMENT_CORRECTED_RERUN",
                timestamp=date.today().isoformat(),
                data_range_accessed=f"DEVELOPMENT ({DEVELOPMENT_SPLIT.start_date} -> {DEVELOPMENT_SPLIT.end_date})",
                metrics_exposed=["trades", "net_pnl", "expectancy_r", "win_rate", "profit_factor", "drawdown"],
                outcome_status=outcome,
                rejection_reason="; ".join(scorecard.rejection_reasons),
                next_permitted_state=next_state,
            )
            ledger.record_entry(ledger_entry)

            rerun_results.append({
                "strategy_id": strat.strategy_id,
                "strategy_name": strat.name,
                "config_hash": strat.config_hash,
                "scorecard": {
                    "executed_trades": scorecard.executed_trades,
                    "net_pnl_inr": float(scorecard.net_pnl_inr),
                    "net_expectancy_r": float(scorecard.net_expectancy_r),
                    "win_rate_pct": scorecard.win_rate_pct,
                    "profit_factor": scorecard.profit_factor,
                    "payoff_ratio": scorecard.payoff_ratio,
                    "cagr_pct": scorecard.cagr_pct,
                    "max_drawdown_pct": scorecard.max_drawdown_pct,
                    "sharpe_ratio": scorecard.sharpe_ratio,
                    "max_single_instrument_profit_share_pct": scorecard.max_single_instrument_profit_share_pct,
                    "max_single_trade_profit_share_pct": scorecard.max_single_trade_profit_share_pct,
                    "gate_pass": scorecard.gate_pass,
                    "outcome_status": scorecard.outcome_status,
                    "rejection_reasons": scorecard.rejection_reasons,
                }
            })

        # Save corrected rerun results and ledger
        with open("scratch/m3b_2_1_corrected_rerun_results.json", "w") as f:
            json.dump(rerun_results, f, indent=2)

        ledger_records = [asdict(e) for e in ledger.entries]
        with open("scratch/m3b_2_1_research_ledger.json", "w") as f:
            json.dump(ledger_records, f, indent=2)

    logger.info("\n=== M3B.2.1 CORRECTED RERUN COMPLETE ===")


if __name__ == "__main__":
    main()
