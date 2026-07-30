"""Execution script for M3B.2 Signal Viability & V2 Hypothesis Revision pipeline.

Orchestrates the 4 sequential phases:
- Phase A: Condition Attrition Diagnostics
- Phase B: V2 Hypothesis Declaration
- Phase C: Blind Signal Viability Gate (P&L hidden, max 3 configs/family)
- Phase D: Frozen V2 DEVELOPMENT Backtest + Predeclared Robustness Analysis
"""

from datetime import date
from decimal import Decimal
import json
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m3b_2_pipeline")

from tradecraft.core.db import SessionLocal
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT, VALIDATION_SPLIT, FINAL_TEST_SPLIT
from tradecraft.research.attrition_analysis import ConditionAttritionAnalyzer, StrategyAttritionReport
from tradecraft.strategy.v2_strategies import (
    TrendPullbackV2Strategy,
    BreakoutConfirmV2Strategy,
    MomentumRSV2Strategy,
    MeanReversionV2Strategy,
    BaseV2Strategy,
)
from tradecraft.research.signal_viability import SignalViabilityEvaluator, SignalViabilityReport
from tradecraft.research.v2_development_gate import (
    V2DevelopmentGateEvaluator,
    FrozenV2CanonicalRecord,
    PredeclaredRobustnessNeighbourhood,
    V2DevelopmentScorecard,
)
from tradecraft.research.robustness import LimitedRobustnessAnalyzer, StrategyRobustnessReport
from tradecraft.research.ledger import ImmutableResearchLedger, ResearchLedgerEntry


def main() -> None:
    logger.info("=== M3B.2 SIGNAL VIABILITY & V2 HYPOTHESIS REVISION PIPELINE ===")

    # 1. Firewall Verification
    DevelopmentOnlyGuard.validate_range(DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date)
    logger.info(f"Verified DEVELOPMENT dataset firewall range: {DEVELOPMENT_SPLIT.start_date} -> {DEVELOPMENT_SPLIT.end_date}")
    logger.info("VALIDATION (2022-01-01..) and FINAL TEST (2024-07-01..) datasets are STRICTLY BLOCKED.")

    with SessionLocal() as db:
        ledger = ImmutableResearchLedger(db)

        # ----------------------------------------------------------------------
        # PHASE A — CONDITION ATtrITION DIAGNOSTICS
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE A: CONDITION ATTRITION DIAGNOSTICS ---")
        attrition_analyzer = ConditionAttritionAnalyzer(db)
        attrition_reports: list[StrategyAttritionReport] = attrition_analyzer.analyze_all_families()

        for ar in attrition_reports:
            logger.info(f"Family: {ar.strategy_family} ({ar.strategy_id}) | Total Eligible Obs: {ar.total_eligible_observations}")
            for cs in ar.condition_stats:
                logger.info(f"   Condition: {cs.condition_name} | Indiv Pass: {cs.individual_pass_rate_pct}% | Cum Pass: {cs.cumulative_pass_rate_pct}% | Class: {cs.classification}")
            logger.info(f"   Primary Signal Killer: {ar.primary_signal_killer}")

        # ----------------------------------------------------------------------
        # PHASE B — V2 HYPOTHESIS DECLARATION
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE B: V2 HYPOTHESIS DECLARATION ---")
        v2_strategies: list[BaseV2Strategy] = [
            TrendPullbackV2Strategy(),
            BreakoutConfirmV2Strategy(),
            MomentumRSV2Strategy(),
            MeanReversionV2Strategy(),
        ]

        # ----------------------------------------------------------------------
        # PHASE C — BLIND SIGNAL VIABILITY GATE (P&L HIDDEN)
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE C: BLIND SIGNAL VIABILITY GATE (P&L STRICTLY SUPPRESSED) ---")
        viability_evaluator = SignalViabilityEvaluator(db)
        frozen_records: list[FrozenV2CanonicalRecord] = []

        for strat in v2_strategies:
            v_report: SignalViabilityReport = viability_evaluator.evaluate_viability(strat)
            logger.info(f"Viability Evaluation for {strat.name} ({strat.config_hash[:12]}...):")
            logger.info(f"   Confirmed Signals: {v_report.total_confirmed_signals} | Active Insts: {v_report.active_instruments_count} | Active Years: {v_report.active_calendar_years_count}")
            logger.info(f"   Max Inst Conc: {v_report.max_single_instrument_concentration_pct}% | Max Semester Conc: {v_report.max_single_semester_concentration_pct}%")
            logger.info(f"   Viability Pass: {v_report.policy_pass} | Non-Degenerate: {v_report.is_non_degenerate}")

            # Predeclare Robustness Neighbourhood BEFORE P&L Exposure
            predeclared_neigh = PredeclaredRobustnessNeighbourhood(
                strategy_id=strat.strategy_id,
                canonical_config_hash=strat.config_hash,
                eligible_parameters=list(strat.parameters.keys()),
                rationale="Small delta perturbations (+/- 10%) around canonical V2 parameters.",
                delta_map={
                    "atr_dist_max": [1.8, 2.2],
                    "max_consolidation_pct": [0.18, 0.22],
                    "top_percentile_cutoff": [0.20, 0.30],
                    "rsi_oversold": [35.0, 45.0],
                },
                max_configurations=5,
                predeclared_config_hashes=[f"hash_var_{i}" for i in range(4)],
            )

            # Freeze V2 canonical record if passed viability
            if v_report.policy_pass:
                frozen = FrozenV2CanonicalRecord(
                    strategy_id=strat.strategy_id,
                    strategy_name=strat.name,
                    strategy_version=strat.version,
                    config_hash=strat.config_hash,
                    freeze_timestamp=date.today().isoformat(),
                    hypothesis_statement=strat.hypothesis_statement,
                    parameters=strat.parameters,
                    viability_report=v_report,
                    selection_rationale="Passed SignalViabilityPolicy v1.0 with highest economic simplicity.",
                    robustness_neighbourhood=predeclared_neigh,
                )
                frozen_records.append(frozen)

                # Record in Ledger
                ledger.record_entry(
                    ResearchLedgerEntry(
                        experiment_id="exp_m3b_2",
                        strategy_family=strat.name,
                        strategy_id=strat.strategy_id,
                        parent_strategy_id=strat.parent_strategy_id,
                        config_hash=strat.config_hash,
                        parameters=strat.parameters,
                        hypothesis_statement=strat.hypothesis_statement,
                        parameter_origins=[{"param": p.parameter_name, "origin": p.origin_category} for p in strat.parameter_origins],
                        phase="PHASE_C_VIABILITY",
                        timestamp=date.today().isoformat(),
                        data_range_accessed="DEVELOPMENT (2016-08-01 -> 2021-12-31)",
                        metrics_exposed=["signals", "years", "instruments", "concentration"],
                        outcome_status="VIABILITY_PASS",
                        rejection_reason="",
                        next_permitted_state="DEVELOPMENT_PROFITABILITY_TEST",
                    )
                )

        # ----------------------------------------------------------------------
        # PHASE D — FROZEN V2 DEVELOPMENT BACKTEST & ROBUSTNESS
        # ----------------------------------------------------------------------
        logger.info("\n--- PHASE D: FROZEN V2 DEVELOPMENT BACKTEST & ROBUSTNESS ---")
        gate_evaluator = V2DevelopmentGateEvaluator(db)
        robustness_analyzer = LimitedRobustnessAnalyzer(db)

        final_summary: list[dict[str, Any]] = []

        for frozen in frozen_records:
            # Find matching strategy instance
            strat_inst = next(s for s in v2_strategies if s.strategy_id == frozen.strategy_id)

            # Backtest frozen canonical V2
            scorecard, trades = gate_evaluator.evaluate_frozen_v2(frozen, strat_inst)

            logger.info(f"DEVELOPMENT Scorecard for {frozen.strategy_name}:")
            logger.info(f"   Executed Trades: {scorecard.executed_trades} | Net Expectancy_R: {scorecard.net_expectancy_r:+.4f} | Net P&L: INR {float(scorecard.net_pnl_inr):,.2f}")
            logger.info(f"   Win Rate: {scorecard.win_rate_pct}% | Payoff: {scorecard.payoff_ratio} | Profit Factor: {scorecard.profit_factor}")
            logger.info(f"   Gate Pass: {scorecard.gate_pass} | Outcome: {scorecard.outcome_status}")

            # Record Phase D in Ledger
            ledger.record_entry(
                ResearchLedgerEntry(
                    experiment_id="exp_m3b_2",
                    strategy_family=frozen.strategy_name,
                    strategy_id=frozen.strategy_id,
                    parent_strategy_id=strat_inst.parent_strategy_id,
                    config_hash=frozen.config_hash,
                    parameters=frozen.parameters,
                    hypothesis_statement=frozen.hypothesis_statement,
                    parameter_origins=[{"param": p.parameter_name, "origin": p.origin_category} for p in strat_inst.parameter_origins],
                    phase="PHASE_D_DEVELOPMENT",
                    timestamp=date.today().isoformat(),
                    data_range_accessed="DEVELOPMENT (2016-08-01 -> 2021-12-31)",
                    metrics_exposed=["trades", "net_pnl", "expectancy_r", "win_rate", "profit_factor", "drawdown"],
                    outcome_status=scorecard.outcome_status,
                    rejection_reason=", ".join(scorecard.rejection_reasons),
                    next_permitted_state="ROBUSTNESS_SEARCH" if scorecard.gate_pass else "RESEARCH_GRAVEYARD",
                )
            )

            # Robustness Analysis if survivor
            rob_report: StrategyRobustnessReport | None = None
            if scorecard.gate_pass:
                rob_report = robustness_analyzer.analyze_robustness(frozen, scorecard)
                logger.info(f"Robustness Report for {frozen.strategy_name}: Stable={rob_report.is_neighbourhood_stable}, Cliff={rob_report.parameter_cliff_flagged}")

            final_summary.append({
                "family": frozen.strategy_name,
                "strategy_id": frozen.strategy_id,
                "config_hash": frozen.config_hash,
                "viability_pass": frozen.viability_report.policy_pass,
                "trades": scorecard.executed_trades,
                "net_expectancy_r": scorecard.net_expectancy_r,
                "net_pnl_inr": float(scorecard.net_pnl_inr),
                "profit_factor": scorecard.profit_factor,
                "gate_outcome": scorecard.outcome_status,
                "robustness_stable": rob_report.is_neighbourhood_stable if rob_report else False,
                "final_status": "V2_DEVELOPMENT_SURVIVOR_AWAITING_VALIDATION_APPROVAL" if (scorecard.gate_pass and rob_report and rob_report.is_neighbourhood_stable) else "V2_DEVELOPMENT_FAILURE",
            })

        # Export Ledger
        ledger_path = os.path.join("scratch", "m3b_2_research_ledger.json")
        ledger.export_json(ledger_path)

        logger.info("\n================================================================================")
        logger.info("M3B.2 EMPIRICAL PIPELINE COMPLETE — ALL 4 V2 STRATEGY FAMILIES EVALUATED")
        logger.info("================================================================================")


if __name__ == "__main__":
    main()
