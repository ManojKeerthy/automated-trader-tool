"""M3B Strategy Research Laboratory Orchestrator.

Implements the two-stage research process, overfitting controls, evaluation-run accounting,
finalist selection, and final test consumption persistence per approved M3B specification.
"""
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine
from tradecraft.backtesting.metrics import MetricValue
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.core.db_models import Experiment, Instrument
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.graveyard import ResearchGraveyardManager, compute_configuration_hash
from tradecraft.research.risk_free_rate import RiskFreeRateConfig
from tradecraft.research.scorecard import ScorecardEvaluator, StrategyScorecard
from tradecraft.research.splits import ChronologicalDataSplitter
from tradecraft.strategy.breakout_confirm import BreakoutConfirmStrategy
from tradecraft.strategy.mean_reversion import MeanReversionStrategy
from tradecraft.strategy.momentum_rs import MomentumRSStrategy
from tradecraft.strategy.trend_pullback import TrendPullbackStrategy

logger = logging.getLogger(__name__)


@runtime_checkable
class EvaluatableStrategy(Protocol):
    """Protocol for strategies that evaluate single instruments or universe."""

    @property
    def strategy_id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def required_history(self) -> int: ...
    @property
    def parameters(self) -> dict[str, Any]: ...


@dataclass
class FamilyResearchSummary:
    family_name: str
    strategy_id: str
    stage_1_passed: bool
    unique_configs_searched: int
    train_runs_count: int
    validation_runs_count: int
    walk_forward_runs_count: int
    friction_runs_count: int
    final_test_runs_count: int
    finalist_config: dict[str, Any] | None = None
    finalist_scorecard: StrategyScorecard | None = None
    final_test_status: str = "NOT_ACCESSED"  # NOT_ACCESSED, ACCESSED_PASSED, ACCESSED_FAILED
    rejection_reason: str | None = None


class M3BResearchLaboratory:
    """Orchestrates the M3B Strategy Research Laboratory."""

    def __init__(
        self,
        db_session: Session,
        calendar: TradingCalendar,
        initial_capital: Decimal = Decimal("1000000.0"),
        rf_config: RiskFreeRateConfig | None = None,
    ):
        self.db = db_session
        self.cal = calendar
        self.initial_capital = initial_capital
        self.rf_config = rf_config or RiskFreeRateConfig()
        self.splitter = ChronologicalDataSplitter()
        self.graveyard = ResearchGraveyardManager(self.db)
        self.scorecard_evaluator = ScorecardEvaluator()

    def run_m3b_research_lab(self) -> dict[str, Any]:
        """Runs the complete M3B research laboratory across all 4 strategy families."""
        logger.info("=== STARTING M3B STRATEGY RESEARCH LABORATORY ===")

        # Create experiment tracking entry
        experiment_id = uuid.uuid4()
        exp = Experiment(
            id=experiment_id,
            name="M3B Master Strategy Research Run",
            description="Sequential 4-family research laboratory evaluation with two-stage overfitting rejection.",
            status="RUNNING",
            metadata_json={"research_quality": "UNVERIFIED_UNIVERSE", "total_unique_configs_limit": 100},
        )
        self.db.add(exp)
        self.db.commit()

        # Load active Nifty 50 instruments
        instruments = self.db.scalars(
            self.db.query(Instrument).filter(Instrument.is_active == True).statement
        ).all()
        inst_ids = [inst.id for inst in instruments]

        if not inst_ids:
            logger.error("No active instruments found in database!")
            return {"error": "NO_INSTRUMENTS"}

        cost_model = IndianEquityDeliveryCostModel()
        engine = BacktestEngine(db_session=self.db, calendar_instance=self.cal)

        summaries: list[FamilyResearchSummary] = []
        total_unique_configs = 0
        total_evaluation_runs = 0

        # Define 4 Family Definitions
        families: list[dict[str, Any]] = [
            {
                "name": "Trend Pullback",
                "id": "strat_trend_pullback",
                "default_cls": TrendPullbackStrategy,
                "canonical_params": {"trend_ma": 50, "pullback_atr_dist": 1.5, "rsi_trigger": 45.0},
                "grid": [
                    {"trend_ma": 20, "pullback_atr_dist": 1.0, "rsi_trigger": 40.0},
                    {"trend_ma": 20, "pullback_atr_dist": 1.5, "rsi_trigger": 45.0},
                    {"trend_ma": 20, "pullback_atr_dist": 2.0, "rsi_trigger": 50.0},
                    {"trend_ma": 50, "pullback_atr_dist": 1.0, "rsi_trigger": 40.0},
                    {"trend_ma": 50, "pullback_atr_dist": 1.5, "rsi_trigger": 45.0},
                    {"trend_ma": 50, "pullback_atr_dist": 2.0, "rsi_trigger": 50.0},
                    {"trend_ma": 100, "pullback_atr_dist": 1.0, "rsi_trigger": 40.0},
                    {"trend_ma": 100, "pullback_atr_dist": 1.5, "rsi_trigger": 45.0},
                    {"trend_ma": 100, "pullback_atr_dist": 2.0, "rsi_trigger": 50.0},
                ],
            },
            {
                "name": "Breakout Confirmation",
                "id": "strat_breakout_confirm",
                "default_cls": BreakoutConfirmStrategy,
                "canonical_params": {"channel_period": 20, "rvol_min": 1.5, "max_consolidation_pct": 0.12},
                "grid": [
                    {"channel_period": 20, "rvol_min": 1.3, "max_consolidation_pct": 0.10},
                    {"channel_period": 20, "rvol_min": 1.5, "max_consolidation_pct": 0.12},
                    {"channel_period": 20, "rvol_min": 1.8, "max_consolidation_pct": 0.15},
                    {"channel_period": 40, "rvol_min": 1.3, "max_consolidation_pct": 0.10},
                    {"channel_period": 40, "rvol_min": 1.5, "max_consolidation_pct": 0.12},
                    {"channel_period": 40, "rvol_min": 1.8, "max_consolidation_pct": 0.15},
                    {"channel_period": 55, "rvol_min": 1.3, "max_consolidation_pct": 0.10},
                    {"channel_period": 55, "rvol_min": 1.5, "max_consolidation_pct": 0.12},
                    {"channel_period": 55, "rvol_min": 1.8, "max_consolidation_pct": 0.15},
                ],
            },
            {
                "name": "Momentum Relative Strength",
                "id": "strat_momentum_rs",
                "default_cls": MomentumRSStrategy,
                "canonical_params": {"rs_lookback": 63, "top_percentile": 0.10, "atr_stop_mult": 2.5},
                "grid": [
                    {"rs_lookback": 21, "top_percentile": 0.05, "atr_stop_mult": 2.0},
                    {"rs_lookback": 21, "top_percentile": 0.10, "atr_stop_mult": 2.5},
                    {"rs_lookback": 21, "top_percentile": 0.15, "atr_stop_mult": 3.0},
                    {"rs_lookback": 63, "top_percentile": 0.05, "atr_stop_mult": 2.0},
                    {"rs_lookback": 63, "top_percentile": 0.10, "atr_stop_mult": 2.5},
                    {"rs_lookback": 63, "top_percentile": 0.15, "atr_stop_mult": 3.0},
                    {"rs_lookback": 126, "top_percentile": 0.05, "atr_stop_mult": 2.0},
                    {"rs_lookback": 126, "top_percentile": 0.10, "atr_stop_mult": 2.5},
                    {"rs_lookback": 126, "top_percentile": 0.15, "atr_stop_mult": 3.0},
                ],
            },
            {
                "name": "Mean Reversion",
                "id": "strat_mean_reversion",
                "default_cls": MeanReversionStrategy,
                "canonical_params": {"rsi_oversold": 30.0, "displacement_atr": 2.0, "max_holding_days": 8},
                "grid": [
                    {"rsi_oversold": 25.0, "displacement_atr": 1.5, "max_holding_days": 5},
                    {"rsi_oversold": 25.0, "displacement_atr": 2.0, "max_holding_days": 8},
                    {"rsi_oversold": 25.0, "displacement_atr": 2.5, "max_holding_days": 10},
                    {"rsi_oversold": 30.0, "displacement_atr": 1.5, "max_holding_days": 5},
                    {"rsi_oversold": 30.0, "displacement_atr": 2.0, "max_holding_days": 8},
                    {"rsi_oversold": 30.0, "displacement_atr": 2.5, "max_holding_days": 10},
                    {"rsi_oversold": 35.0, "displacement_atr": 1.5, "max_holding_days": 5},
                    {"rsi_oversold": 35.0, "displacement_atr": 2.0, "max_holding_days": 8},
                    {"rsi_oversold": 35.0, "displacement_atr": 2.5, "max_holding_days": 10},
                ],
            },
        ]

        for fam in families:
            f_name: str = str(fam["name"])
            f_id: str = str(fam["id"])
            f_cls: Any = fam["default_cls"]
            f_canon: dict[str, Any] = fam["canonical_params"]
            f_grid: list[dict[str, Any]] = fam["grid"]

            logger.info(f"\n=== EVALUATING FAMILY: {f_name} ({f_id}) ===")

            summary = FamilyResearchSummary(
                family_name=f_name,
                strategy_id=f_id,
                stage_1_passed=False,
                unique_configs_searched=0,
                train_runs_count=0,
                validation_runs_count=0,
                walk_forward_runs_count=0,
                friction_runs_count=0,
                final_test_runs_count=0,
            )

            # --- STAGE 1: Canonical Hypothesis Test on TRAIN ---
            canon_strat = f_cls(**f_canon)
            summary.unique_configs_searched += 1
            total_unique_configs += 1

            config_stage1 = BacktestConfig(
                strategy=canon_strat,
                start_date=self.splitter.train_split.start_date,
                end_date=self.splitter.train_split.end_date,
                initial_capital=self.initial_capital,
                cost_model=cost_model,
                slippage_model=FixedBasisPointSlippage(bps=5),
                risk_free_config=self.rf_config,
            )

            train_res = engine.run(config_stage1)
            summary.train_runs_count += 1
            total_evaluation_runs += 1

            train_metrics = train_res.metrics.metrics
            exp_r_metric = train_metrics.get("expectancy_r")
            max_dd_metric = train_metrics.get("max_drawdown_pct")

            exp_r_val = exp_r_metric.value if isinstance(exp_r_metric, MetricValue) else None
            max_dd_val = max_dd_metric.value if isinstance(max_dd_metric, MetricValue) else None

            exp_r_float = float(exp_r_val) if exp_r_val is not None else 0.0
            max_dd_float = float(max_dd_val) if max_dd_val is not None else 100.0

            # Stage 1 Gate
            if exp_r_float <= 0.0 or max_dd_float > 25.0:
                summary.stage_1_passed = False
                summary.rejection_reason = "STAGE_1_CANONICAL_FAILURE"
                self.graveyard.record_rejection(
                    strategy_id=f_id,
                    strategy_family=f_name,
                    strategy_version=canon_strat.version,
                    parameters=f_canon,
                    rejection_reason_code="NEGATIVE_EXPECTANCY" if exp_r_float <= 0.0 else "EXCESSIVE_DRAWDOWN",
                    rejection_details={"expectancy_r": exp_r_float, "max_drawdown_pct": max_dd_float},
                    stage_failed="STAGE_1",
                )
                logger.info(f"Family {f_name} FAILED Stage 1 Canonical Test. Skipping parameter grid search.")
                summaries.append(summary)
                continue

            summary.stage_1_passed = True
            logger.info(f"Family {f_name} PASSED Stage 1 Canonical Test (Expectancy_R: {exp_r_float:.3f}, Max DD: {max_dd_float:.1f}%).")

            # --- STAGE 2: Limited Parameter Robustness Search on TRAIN ---
            stage_2_results = []
            for p_set in f_grid:
                if total_unique_configs >= 100:
                    logger.warning("Reached maximum overall unique configurations limit (100). Stopping grid search.")
                    break

                summary.unique_configs_searched += 1
                total_unique_configs += 1

                grid_strat = f_cls(**p_set)
                config_grid = BacktestConfig(
                    strategy=grid_strat,
                    start_date=self.splitter.train_split.start_date,
                    end_date=self.splitter.train_split.end_date,
                    initial_capital=self.initial_capital,
                    cost_model=cost_model,
                    slippage_model=FixedBasisPointSlippage(bps=5),
                    risk_free_config=self.rf_config,
                )

                t_res = engine.run(config_grid)
                summary.train_runs_count += 1
                total_evaluation_runs += 1

                t_m = t_res.metrics.metrics
                t_exp_m = t_m.get("expectancy_r")
                t_sharpe_m = t_m.get("sharpe_ratio")
                t_trades_m = t_m.get("trade_count")

                t_exp = float(t_exp_m.value) if t_exp_m and t_exp_m.value is not None else 0.0
                t_sharpe = float(t_sharpe_m.value) if t_sharpe_m and t_sharpe_m.value is not None else 0.0
                t_trades = int(t_trades_m.value) if t_trades_m and t_trades_m.value is not None else 0

                stage_2_results.append({
                    "params": p_set,
                    "strat": grid_strat,
                    "train_res": t_res,
                    "train_exp_r": t_exp,
                    "train_sharpe": t_sharpe,
                    "train_trades": t_trades,
                })

            # Sort Stage 2 candidates by Expectancy_R on TRAIN
            stage_2_results.sort(key=lambda x: x["train_exp_r"], reverse=True)

            # Filter top candidate for Out-of-Sample Validation & Walk-Forward
            best_candidate = stage_2_results[0] if stage_2_results else None

            if not best_candidate or best_candidate["train_exp_r"] <= 0.0:
                summary.rejection_reason = "STAGE_2_NO_POSITIVE_CANDIDATE"
                summaries.append(summary)
                continue

            # --- VALIDATION EVALUATION ---
            config_val = BacktestConfig(
                strategy=best_candidate["strat"],
                start_date=self.splitter.validation_split.start_date,
                end_date=self.splitter.validation_split.end_date,
                initial_capital=self.initial_capital,
                cost_model=cost_model,
                slippage_model=FixedBasisPointSlippage(bps=5),
                risk_free_config=self.rf_config,
            )
            val_res = engine.run(config_val)
            summary.validation_runs_count += 1
            total_evaluation_runs += 1

            # --- WALK-FORWARD EVALUATION ---
            wf_windows = self.splitter.generate_walk_forward_windows()
            wf_positive_count = 0
            for w in wf_windows:
                config_wf = BacktestConfig(
                    strategy=best_candidate["strat"],
                    start_date=w.test_start,
                    end_date=w.test_end,
                    initial_capital=self.initial_capital,
                    cost_model=cost_model,
                    slippage_model=FixedBasisPointSlippage(bps=5),
                    risk_free_config=self.rf_config,
                )
                w_res = engine.run(config_wf)
                summary.walk_forward_runs_count += 1
                total_evaluation_runs += 1

                w_exp_m = w_res.metrics.metrics.get("expectancy_r")
                w_exp = float(w_exp_m.value) if w_exp_m and w_exp_m.value is not None else 0.0
                if w_exp > 0.0:
                    wf_positive_count += 1

            wf_pct = (wf_positive_count / len(wf_windows)) * 100.0 if wf_windows else 0.0

            # --- FRICTION STRESS EVALUATION (10 bps) ---
            config_stress = BacktestConfig(
                strategy=best_candidate["strat"],
                start_date=self.splitter.validation_split.start_date,
                end_date=self.splitter.validation_split.end_date,
                initial_capital=self.initial_capital,
                cost_model=cost_model,
                slippage_model=FixedBasisPointSlippage(bps=10),
                risk_free_config=self.rf_config,
            )
            stress_res = engine.run(config_stress)
            summary.friction_runs_count += 1
            total_evaluation_runs += 1

            stress_pf_m = stress_res.metrics.metrics.get("profit_factor")
            stress_pf = float(stress_pf_m.value) if stress_pf_m and stress_pf_m.value is not None else 1.0

            # Evaluate Scorecard BEFORE Final Test
            val_m = val_res.metrics.metrics
            v_exp_m = val_m.get("expectancy_r")
            v_sharpe_m = val_m.get("sharpe_ratio")
            v_dd_m = val_m.get("max_drawdown_pct")
            v_trades_m = val_m.get("trade_count")

            val_exp_r = Decimal(str(v_exp_m.value)) if v_exp_m and v_exp_m.value is not None else Decimal("0.0")
            val_sharpe = Decimal(str(v_sharpe_m.value)) if v_sharpe_m and v_sharpe_m.value is not None else Decimal("0.0")
            val_dd = Decimal(str(v_dd_m.value)) if v_dd_m and v_dd_m.value is not None else Decimal("0.0")
            val_trades = int(v_trades_m.value) if v_trades_m and v_trades_m.value is not None else 0

            scorecard = self.scorecard_evaluator.evaluate(
                strategy_id=f_id,
                strategy_version=best_candidate["strat"].version,
                config_hash=compute_configuration_hash(f_id, best_candidate["params"]),
                train_sharpe=Decimal(str(best_candidate["train_sharpe"])),
                val_sharpe=val_sharpe,
                train_expectancy_r=Decimal(str(best_candidate["train_exp_r"])),
                val_expectancy_r=val_exp_r,
                max_drawdown=val_dd,
                walk_forward_positive_pct=Decimal(str(wf_pct)),
                stressed_pf_10bps=Decimal(str(stress_pf)),
                total_trades=val_trades,
            )

            # FINALIST SELECTION GATING (Max 1 Finalist per Family)
            if scorecard.overall_rating in ("STRONG", "ACCEPTABLE"):
                summary.finalist_config = best_candidate["params"]
                summary.finalist_scorecard = scorecard

                logger.info(f"Selected FINALIST for {f_name}: Scorecard Rating = {scorecard.overall_rating}")

                # --- FINAL TEST EVALUATION (Accessed ONLY by selected finalist) ---
                config_final = BacktestConfig(
                    strategy=best_candidate["strat"],
                    start_date=self.splitter.final_test_split.start_date,
                    end_date=self.splitter.final_test_split.end_date,
                    initial_capital=self.initial_capital,
                    cost_model=cost_model,
                    slippage_model=FixedBasisPointSlippage(bps=5),
                    risk_free_config=self.rf_config,
                )
                final_res = engine.run(config_final)
                summary.final_test_runs_count += 1
                total_evaluation_runs += 1

                final_m = final_res.metrics.metrics
                final_exp_m = final_m.get("expectancy_r")
                final_exp_r = float(final_exp_m.value) if final_exp_m and final_exp_m.value is not None else 0.0

                if final_exp_r > 0.0:
                    summary.final_test_status = "ACCESSED_PASSED"
                    logger.info(f"FINAL TEST PASSED for {f_name}! (Final Expectancy_R: {final_exp_r:.3f})")
                else:
                    summary.final_test_status = "ACCESSED_FAILED"
                    summary.rejection_reason = "FINAL_TEST_FAILURE"
                    self.graveyard.record_rejection(
                        strategy_id=f_id,
                        strategy_family=f_name,
                        strategy_version=best_candidate["strat"].version,
                        parameters=best_candidate["params"],
                        rejection_reason_code="OUT_OF_SAMPLE_FAILURE",
                        rejection_details={"final_test_expectancy_r": final_exp_r},
                        stage_failed="FINAL_TEST",
                    )
                    logger.info(f"FINAL TEST FAILED for {f_name}. Recorded in Graveyard. No retuning permitted.")
            else:
                summary.rejection_reason = f"SCORECARD_REJECTED_{scorecard.overall_rating}"
                self.graveyard.record_rejection(
                    strategy_id=f_id,
                    strategy_family=f_name,
                    strategy_version=best_candidate["strat"].version,
                    parameters=best_candidate["params"],
                    rejection_reason_code=f"SCORECARD_{scorecard.overall_rating}",
                    rejection_details={"scorecard": scorecard.to_dict()},
                    stage_failed="VALIDATION",
                )
                logger.info(f"Family {f_name} candidate REJECTED by Scorecard ({scorecard.overall_rating}). Did NOT access Final Test.")

            summaries.append(summary)

        # Update experiment status
        exp.status = "COMPLETED"
        exp.metadata_json = {
            "research_quality": "UNVERIFIED_UNIVERSE",
            "total_unique_configs_searched": total_unique_configs,
            "total_evaluation_runs": total_evaluation_runs,
            "final_test_consumed": True,
        }
        self.db.commit()

        logger.info("\n=== M3B STRATEGY RESEARCH LABORATORY COMPLETED ===")
        logger.info(f"Total Unique Strategy Configurations Searched: {total_unique_configs} / 100 max")
        logger.info(f"Total Evaluation Runs Executed: {total_evaluation_runs}")

        return {
            "experiment_id": str(experiment_id),
            "status": "COMPLETED",
            "total_unique_configs_searched": total_unique_configs,
            "total_evaluation_runs": total_evaluation_runs,
            "summaries": [
                {
                    "family_name": s.family_name,
                    "strategy_id": s.strategy_id,
                    "stage_1_passed": s.stage_1_passed,
                    "unique_configs_searched": s.unique_configs_searched,
                    "train_runs_count": s.train_runs_count,
                    "validation_runs_count": s.validation_runs_count,
                    "walk_forward_runs_count": s.walk_forward_runs_count,
                    "friction_runs_count": s.friction_runs_count,
                    "final_test_runs_count": s.final_test_runs_count,
                    "final_test_status": s.final_test_status,
                    "rejection_reason": s.rejection_reason,
                    "finalist_config": s.finalist_config,
                    "scorecard": s.finalist_scorecard.to_dict() if s.finalist_scorecard else None,
                }
                for s in summaries
            ],
        }
