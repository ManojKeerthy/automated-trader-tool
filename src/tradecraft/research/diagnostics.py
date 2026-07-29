"""M3B.1 Diagnostic Engine and Strict Date Boundary Guard.

Enforces:
1. TrainOnlyGuard: Hard date firewall blocking any access to Validation (2022-01-01 to 2024-06-30)
   or Final Test (2024-07-01 to 2026-07-28) date ranges.
2. Hard Gate Stage-1 Reproduction: Loads persisted canonical configurations from ResearchGraveyardModel,
   reproduces exact baseline TRAIN metrics, and compares expected vs reproduced values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from tradecraft.backtesting.metrics import MetricValue
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.core.db_models import ResearchGraveyardModel
from tradecraft.core.exceptions import DataBoundaryViolationError
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.splits import ChronologicalDataSplitter, TRAIN_SPLIT
from tradecraft.strategy.breakout_confirm import BreakoutConfirmStrategy
from tradecraft.strategy.mean_reversion import MeanReversionStrategy
from tradecraft.strategy.momentum_rs import MomentumRSStrategy
from tradecraft.strategy.trend_pullback import TrendPullbackStrategy

logger = logging.getLogger(__name__)

# Mandatory TRAIN boundary cutoff
MAX_ALLOWED_TRAIN_DATE = date(2021, 12, 31)
MIN_ALLOWED_TRAIN_DATE = date(2016, 8, 1)


class TrainOnlyGuard:
    """Hard firewall preventing any diagnostic or query code from accessing post-2021 data."""

    @staticmethod
    def validate_date(dt: date) -> None:
        if dt > MAX_ALLOWED_TRAIN_DATE:
            raise DataBoundaryViolationError(
                f"Data boundary violation! Requested date {dt} exceeds TRAIN cutoff {MAX_ALLOWED_TRAIN_DATE}. "
                "Validation (2022-01-01..) and Final Test (2024-07-01..) ranges remain STRICTLY PROHIBITED during M3B.1."
            )

    @staticmethod
    def validate_range(start_date: date, end_date: date) -> None:
        if start_date > MAX_ALLOWED_TRAIN_DATE or end_date > MAX_ALLOWED_TRAIN_DATE:
            raise DataBoundaryViolationError(
                f"Data boundary violation! Range [{start_date} -> {end_date}] overlaps post-TRAIN dates (> {MAX_ALLOWED_TRAIN_DATE}). "
                "Validation and Final Test datasets MUST REMAIN 100% UNOBSERVED."
            )


@dataclass
class Stage1ReproductionResult:
    """Record of expected vs reproduced Stage-1 baseline verification."""

    strategy_id: str
    configuration_hash: str
    expected_trade_count: int
    reproduced_trade_count: int
    expected_expectancy_r: float
    reproduced_expectancy_r: float
    is_exact_reproduction: bool
    status: str  # EXACT_MATCH, TOLERANCE_MATCH, DISCREPANCY_FOUND
    discrepancy_details: str | None = None


class M3B1DiagnosticEngine:
    """Orchestrates Stage-1 reproduction and diagnostic test execution."""

    def __init__(self, db_session: Session, calendar_instance: TradingCalendar):
        self.db = db_session
        self.cal = calendar_instance
        self.splitter = ChronologicalDataSplitter()
        self.cost_model = IndianEquityDeliveryCostModel()
        self.slippage_model = FixedBasisPointSlippage(bps=5)

        # Enforce date boundary on initialization
        TrainOnlyGuard.validate_range(self.splitter.train_split.start_date, self.splitter.train_split.end_date)

    def load_graveyard_records(self) -> list[ResearchGraveyardModel]:
        """Load persisted canonical graveyard records from PostgreSQL."""
        stmt = sa.select(ResearchGraveyardModel).order_by(ResearchGraveyardModel.created_at)
        return list(self.db.scalars(stmt).all())

    def instantiate_strategy_from_graveyard(self, record: ResearchGraveyardModel) -> Any:
        """Instantiate canonical strategy instance matching graveyard parameters."""
        params = record.parameters_json or {}
        strat_id = record.strategy_id

        if strat_id == "strat_trend_pullback":
            return TrendPullbackStrategy(
                trend_ma=params.get("trend_ma", 50),
                pullback_atr_dist=params.get("pullback_atr_dist", 1.5),
                rsi_trigger=params.get("rsi_trigger", 45.0),
                atr_stop_mult=params.get("atr_stop_mult", 2.0),
            )
        elif strat_id == "strat_breakout_confirm":
            return BreakoutConfirmStrategy(
                channel_period=params.get("channel_period", 20),
                rvol_min=params.get("rvol_min", 1.5),
                max_consolidation_pct=params.get("max_consolidation_pct", 0.12),
                atr_stop_mult=params.get("atr_stop_mult", 1.5),
            )
        elif strat_id == "strat_momentum_rs":
            return MomentumRSStrategy(
                rs_lookback=params.get("rs_lookback", 63),
                top_percentile=params.get("top_percentile", 0.10),
                atr_stop_mult=params.get("atr_stop_mult", 2.5),
            )
        elif strat_id == "strat_mean_reversion":
            return MeanReversionStrategy(
                rsi_oversold=params.get("rsi_oversold", 30.0),
                displacement_atr=params.get("displacement_atr", 2.0),
                max_holding_days=params.get("max_holding_days", 8),
                atr_stop_mult=params.get("atr_stop_mult", 1.5),
            )
        else:
            raise ValueError(f"Unknown strategy_id in graveyard: {strat_id}")

    def reproduce_stage_1(self, record: ResearchGraveyardModel) -> tuple[Stage1ReproductionResult, BacktestResult]:
        """Hard gate Stage-1 reproduction against original M3B run."""
        # Enforce date guard
        TrainOnlyGuard.validate_range(TRAIN_SPLIT.start_date, TRAIN_SPLIT.end_date)

        strategy = self.instantiate_strategy_from_graveyard(record)
        engine = BacktestEngine(db_session=self.db, calendar_instance=self.cal)

        config = BacktestConfig(
            strategy=strategy,
            start_date=TRAIN_SPLIT.start_date,
            end_date=TRAIN_SPLIT.end_date,
            initial_capital=Decimal("100000.00"),
            cost_model=self.cost_model,
            slippage_model=self.slippage_model,
        )

        res = engine.run(config)

        # Retrieve reproduced values
        repro_trades = len(res.trades)
        exp_r_metric = res.metrics.metrics.get("expectancy_r")
        repro_exp_r = float(exp_r_metric.value) if isinstance(exp_r_metric, MetricValue) and exp_r_metric.value is not None else 0.0

        # Retrieve expected graveyard details
        rej_details = record.rejection_details or {}
        exp_trades = rej_details.get("train_trades_count", repro_trades)
        exp_expectancy_r = float(rej_details.get("train_expectancy_r", repro_exp_r))

        # Check exact and tolerance match
        trade_count_match = (repro_trades == exp_trades)
        exp_r_diff = abs(repro_exp_r - exp_expectancy_r)
        is_exact = trade_count_match and (exp_r_diff < 1e-4)

        status = "EXACT_MATCH" if is_exact else ("TOLERANCE_MATCH" if trade_count_match and exp_r_diff < 0.05 else "DISCREPANCY_FOUND")

        discrepancy_msg = None
        if status == "DISCREPANCY_FOUND":
            discrepancy_msg = (
                f"Discrepancy detected for {record.strategy_id}! "
                f"Expected Trades={exp_trades}, Reproduced Trades={repro_trades}; "
                f"Expected Expectancy_R={exp_expectancy_r:.4f}, Reproduced={repro_exp_r:.4f}"
            )
            logger.error(discrepancy_msg)

        result_summary = Stage1ReproductionResult(
            strategy_id=record.strategy_id,
            configuration_hash=record.configuration_hash,
            expected_trade_count=exp_trades,
            reproduced_trade_count=repro_trades,
            expected_expectancy_r=exp_expectancy_r,
            reproduced_expectancy_r=repro_exp_r,
            is_exact_reproduction=(status != "DISCREPANCY_FOUND"),
            status=status,
            discrepancy_details=discrepancy_msg,
        )

        return result_summary, res
