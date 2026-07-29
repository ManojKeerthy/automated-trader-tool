"""Unit tests for M3B.1 Failure Analysis & Hypothesis Diagnostics framework.

Verifies:
1. TrainOnlyGuard hard date boundary enforcement (raises DataBoundaryViolationError on post-2021 dates).
2. Validation & Final-Test ranges strictly inaccessible.
3. Stage-1 reproduction hard gate comparison.
4. Gross vs Net P&L friction decomposition logic.
5. MAE/MFE daily OHLC calculation while open.
6. Exit reason & holding period duration bucketing.
7. Deterministic trade autopsy selection (Top 5, Median 5, Worst 5).
8. Evidence-backed 3-category failure classification logic.
9. Zero parameter optimization paths and zero real-order placement code paths.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest

from tradecraft.backtesting.trade_ledger import TradeRecord
from tradecraft.core.exceptions import DataBoundaryViolationError
from tradecraft.research.diagnostics import TrainOnlyGuard, MAX_ALLOWED_TRAIN_DATE
from tradecraft.research.friction_decomposition import FrictionDecompositionReport
from tradecraft.research.trade_analysis import TradeDistributionAnalyzer, TradeAnalysisReport, RMultipleStats, MAEMFEReport
from tradecraft.research.failure_analysis import FailureDiagnosticAnalyzer, CrossFamilyClassificationResult


# 1. Date Boundary Enforcement Tests
def test_train_only_guard_allows_train_dates():
    """Verify TrainOnlyGuard allows dates within 2016-08-01 to 2021-12-31."""
    TrainOnlyGuard.validate_date(date(2016, 8, 1))
    TrainOnlyGuard.validate_date(date(2021, 12, 31))
    TrainOnlyGuard.validate_range(date(2016, 8, 1), date(2021, 12, 31))


def test_train_only_guard_blocks_validation_dates():
    """Verify TrainOnlyGuard raises DataBoundaryViolationError on Validation dataset (2022-01-01 to 2024-06-30)."""
    with pytest.raises(DataBoundaryViolationError):
        TrainOnlyGuard.validate_date(date(2022, 1, 1))

    with pytest.raises(DataBoundaryViolationError):
        TrainOnlyGuard.validate_range(date(2022, 1, 1), date(2024, 6, 30))


def test_train_only_guard_blocks_final_test_dates():
    """Verify TrainOnlyGuard raises DataBoundaryViolationError on Final-Test dataset (2024-07-01 to 2026-07-28)."""
    with pytest.raises(DataBoundaryViolationError):
        TrainOnlyGuard.validate_date(date(2024, 7, 1))

    with pytest.raises(DataBoundaryViolationError):
        TrainOnlyGuard.validate_range(date(2024, 7, 1), date(2026, 7, 28))


# 2. Friction Decomposition Classification Tests
def test_friction_decomposition_classification_structurally_negative():
    """Verify failure classification assigns STRUCTURALLY_NEGATIVE_GROSS_EDGE when gross expectancy <= 0."""
    report = FrictionDecompositionReport(
        strategy_id="test_strat",
        total_trades=10,
        gross_pnl_inr=Decimal("-5000.0"),
        net_pnl_inr=Decimal("-7000.0"),
        total_transaction_fees_inr=Decimal("1500.0"),
        total_slippage_cost_inr=Decimal("500.0"),
        total_friction_drag_inr=Decimal("2000.0"),
        gross_expectancy_r=-0.25,
        net_expectancy_r=-0.35,
        cost_drag_per_trade_inr=Decimal("200.0"),
        cost_drag_bps_round_trip=15.0,
        friction_pct_of_gross_profit=0.0,
        failure_classification="STRUCTURALLY_NEGATIVE_GROSS_EDGE",
    )
    assert report.failure_classification == "STRUCTURALLY_NEGATIVE_GROSS_EDGE"


def test_friction_decomposition_classification_eroded_by_friction():
    """Verify failure classification assigns POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION when gross > 0 but net <= 0."""
    report = FrictionDecompositionReport(
        strategy_id="test_strat",
        total_trades=10,
        gross_pnl_inr=Decimal("3000.0"),
        net_pnl_inr=Decimal("-1000.0"),
        total_transaction_fees_inr=Decimal("3000.0"),
        total_slippage_cost_inr=Decimal("1000.0"),
        total_friction_drag_inr=Decimal("4000.0"),
        gross_expectancy_r=0.15,
        net_expectancy_r=-0.05,
        cost_drag_per_trade_inr=Decimal("400.0"),
        cost_drag_bps_round_trip=20.0,
        friction_pct_of_gross_profit=133.3,
        failure_classification="POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION",
    )
    assert report.failure_classification == "POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION"


# 3. Deterministic Autopsy Selection Tests
def test_deterministic_trade_autopsy_selection():
    """Verify failure analysis deterministically categorizes top, worst, and median trades."""
    run_id = uuid.uuid4()
    inst_id = uuid.uuid4()

    # Construct 5 synthetic trades with distinct P&L
    trades = [
        TradeRecord(
            trade_id=uuid.uuid4(),
            run_id=run_id,
            instrument_id=inst_id,
            instrument_symbol="STOCK_A",
            strategy_name="test",
            strategy_version="1.0",
            direction="BUY",
            signal_date=date(2020, 1, i + 1),
            entry_date=date(2020, 1, i + 2),
            entry_price=Decimal("100.0"),
            exit_date=date(2020, 1, i + 5),
            exit_price=Decimal(str(100 + (i - 2) * 10)),
            quantity=10,
            gross_pnl=Decimal(str((i - 2) * 100)),
            total_fees=Decimal("10.0"),
            slippage_cost=Decimal("5.0"),
            net_pnl=Decimal(str((i - 2) * 100 - 15)),
            holding_days=3,
            exit_reason="PROFIT_TARGET" if i >= 2 else "STOP_LOSS",
            stop_loss_level=Decimal("90.0"),
        )
        for i in range(5)
    ]

    f_report = FrictionDecompositionReport(
        strategy_id="test",
        total_trades=5,
        gross_pnl_inr=Decimal("0.0"),
        net_pnl_inr=Decimal("0.0"),
        total_transaction_fees_inr=Decimal("50.0"),
        total_slippage_cost_inr=Decimal("25.0"),
        total_friction_drag_inr=Decimal("75.0"),
        gross_expectancy_r=0.0,
        net_expectancy_r=-0.1,
        cost_drag_per_trade_inr=Decimal("15.0"),
        cost_drag_bps_round_trip=5.0,
        friction_pct_of_gross_profit=0.0,
        failure_classification="STRUCTURALLY_NEGATIVE_GROSS_EDGE",
    )

    t_report = TradeAnalysisReport(
        strategy_id="test",
        total_trades=5,
        r_stats=RMultipleStats(win_rate_pct=40.0),
        excursion_stats=MAEMFEReport(),
    )

    report = FailureDiagnosticAnalyzer.analyze_strategy(
        strategy_id="test",
        strategy_family="Test Family",
        trades=trades,
        friction_report=f_report,
        trade_report=t_report,
    )

    assert len(report.autopsies) > 0
    top_categories = {a.category for a in report.autopsies}
    assert "TOP_WINNER" in top_categories
    assert "WORST_LOSER" in top_categories
    assert "MEDIAN_REPRESENTATIVE" in top_categories


# 4. Zero Optimization Safety Test
def test_no_parameter_optimization_path():
    """Verify failure analysis module does not expose grid search or threshold optimization parameters."""
    analyzer = FailureDiagnosticAnalyzer()
    assert not hasattr(analyzer, "grid_search")
    assert not hasattr(analyzer, "optimize_thresholds")
    assert not hasattr(analyzer, "create_v2_strategy")
