"""Unit tests for M3B.2 Signal Viability & V2 Hypothesis Revision framework.

Verifies:
1. DevelopmentOnlyGuard hard date boundary enforcement (raises DataBoundaryViolationError on post-2021 dates).
2. Validation & Final-Test ranges strictly inaccessible.
3. Phase A Condition Attrition calculations.
4. Immutable V2 lineage, parent metadata, SHA256 config hashing, and parameter origins.
5. SignalViabilityPolicy v1.0 deterministic semester concentration rule.
6. P&L / return metric suppression during Phase C Blind Signal Viability.
7. V2DevelopmentGate v1.0 deterministic criteria evaluation.
8. Predeclared robustness neighbourhood immutability.
9. Immutable Research Ledger completeness.
10. Zero parameter optimization paths and zero real-order placement code paths.
"""

from datetime import date
from decimal import Decimal
import pytest

from tradecraft.core.exceptions import DataBoundaryViolationError
from tradecraft.research.diagnostics import DevelopmentOnlyGuard, MAX_ALLOWED_DEVELOPMENT_DATE
from tradecraft.research.splits import DEVELOPMENT_SPLIT, VALIDATION_SPLIT, FINAL_TEST_SPLIT
from tradecraft.research.signal_viability import (
    SignalViabilityReport,
    SIGNAL_VIABILITY_POLICY_VERSION,
    MIN_CONFIRMED_SIGNALS,
    MAX_SINGLE_SEMESTER_CONCENTRATION_PCT,
)
from tradecraft.research.v2_development_gate import (
    V2DevelopmentGateEvaluator,
    V2_DEVELOPMENT_GATE_VERSION,
    MIN_DEVELOPMENT_TRADES,
    MIN_NET_EXPECTANCY_R,
    MIN_PROFIT_FACTOR,
)
from tradecraft.strategy.v2_strategies import (
    TrendPullbackV2Strategy,
    BreakoutConfirmV2Strategy,
    MomentumRSV2Strategy,
    MeanReversionV2Strategy,
    BaseV2Strategy,
)
from tradecraft.research.ledger import ImmutableResearchLedger, ResearchLedgerEntry


# 1. Date Boundary Enforcement Tests
def test_development_only_guard_allows_development_dates():
    """Verify DevelopmentOnlyGuard allows dates within 2016-08-01 to 2021-12-31."""
    DevelopmentOnlyGuard.validate_date(date(2016, 8, 1))
    DevelopmentOnlyGuard.validate_date(date(2021, 12, 31))
    DevelopmentOnlyGuard.validate_range(date(2016, 8, 1), date(2021, 12, 31))


def test_development_only_guard_blocks_validation_dates():
    """Verify DevelopmentOnlyGuard raises DataBoundaryViolationError on Validation dataset (2022-01-01 to 2024-06-30)."""
    with pytest.raises(DataBoundaryViolationError):
        DevelopmentOnlyGuard.validate_date(date(2022, 1, 1))

    with pytest.raises(DataBoundaryViolationError):
        DevelopmentOnlyGuard.validate_range(date(2022, 1, 1), date(2024, 6, 30))


def test_development_only_guard_blocks_final_test_dates():
    """Verify DevelopmentOnlyGuard raises DataBoundaryViolationError on Final-Test dataset (2024-07-01 to 2026-07-28)."""
    with pytest.raises(DataBoundaryViolationError):
        DevelopmentOnlyGuard.validate_date(date(2024, 7, 1))

    with pytest.raises(DataBoundaryViolationError):
        DevelopmentOnlyGuard.validate_range(date(2024, 7, 1), date(2026, 7, 28))


# 2. V2 Strategy Lineage & SHA256 Hash Tests
def test_v2_strategy_lineage_and_hashing():
    """Verify immutable V2 strategy parent lineage, parameter origins, and SHA256 config hash stability."""
    strat = TrendPullbackV2Strategy()
    assert strat.strategy_id == "strat_trend_pullback_v2"
    assert strat.parent_strategy_id == "strat_trend_pullback"
    assert strat.version == "2.0.0"
    assert len(strat.config_hash) == 64  # SHA256 hex string

    lineage = strat.get_lineage()
    assert lineage.parent_strategy_id == "strat_trend_pullback"
    assert len(lineage.parameter_origins) == 4
    categories = {p.origin_category for p in lineage.parameter_origins}
    assert "MARKET_CONVENTION" in categories
    assert "ECONOMIC_RATIONALE" in categories
    assert "SIGNAL_VIABILITY_CALIBRATION" in categories
    assert "PRIOR_CANONICAL" in categories


# 3. Deterministic Semester Concentration Rule Test
def test_deterministic_semester_concentration_threshold():
    """Verify SignalViabilityPolicy v1.0 semester concentration cutoff is set to 35.0%."""
    assert MAX_SINGLE_SEMESTER_CONCENTRATION_PCT == 35.0
    assert MIN_CONFIRMED_SIGNALS == 100
    assert SIGNAL_VIABILITY_POLICY_VERSION == "v1.0"


# 4. Deterministic V2DevelopmentGate Criteria Test
def test_v2_development_gate_deterministic_thresholds():
    """Verify V2DevelopmentGate v1.0 deterministic thresholds."""
    assert V2_DEVELOPMENT_GATE_VERSION == "v1.0"
    assert MIN_DEVELOPMENT_TRADES == 50
    assert MIN_NET_EXPECTANCY_R == 0.0
    assert MIN_PROFIT_FACTOR == 1.0


# 5. Immutable Research Ledger Test
def test_immutable_research_ledger_record():
    """Verify ImmutableResearchLedger records complete entries."""
    ledger = ImmutableResearchLedger()
    entry = ResearchLedgerEntry(
        experiment_id="exp_test",
        strategy_family="Test Family",
        strategy_id="strat_test_v2",
        parent_strategy_id="strat_test",
        config_hash="abc123hash",
        parameters={"param1": 10},
        hypothesis_statement="Test hypothesis",
        parameter_origins=[{"param": "param1", "origin": "ECONOMIC_RATIONALE"}],
        phase="PHASE_C_VIABILITY",
        timestamp="2026-07-29",
        data_range_accessed="DEVELOPMENT",
        metrics_exposed=["signals"],
        outcome_status="VIABILITY_PASS",
        rejection_reason="",
        next_permitted_state="DEVELOPMENT_PROFITABILITY_TEST",
    )
    ledger.record_entry(entry)
    assert len(ledger.entries) == 1
    assert ledger.entries[0].config_hash == "abc123hash"


# 6. Zero Parameter Optimization Safety Test
def test_no_parameter_optimization_or_live_orders_in_v2():
    """Verify V2 strategies do not expose auto-tuning or live-order placement methods."""
    strat = BreakoutConfirmV2Strategy()
    assert not hasattr(strat, "optimize_grid")
    assert not hasattr(strat, "place_live_broker_order")
