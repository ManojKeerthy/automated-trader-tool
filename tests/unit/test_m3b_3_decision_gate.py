"""Unit tests for Milestone M3B.3 — Development Research Decision Gate & Final Hypothesis Triage."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest

from tradecraft.research.splits import DEVELOPMENT_SPLIT, VALIDATION_SPLIT, FINAL_TEST_SPLIT
from tradecraft.research.firewall import DevelopmentDataFirewall, DataBoundaryViolationError
from tradecraft.research.decision_policy import (
    M3B3DecisionPolicy,
    DecisionStatus,
    YearlyStabilityClassification,
    OutlierDependenceClassification,
    CostRobustnessClassification,
    StrategyEvidencePackage,
)
from tradecraft.research.gate_audit import GateProvenanceAuditor, GateProvenanceClassification
from tradecraft.strategy.v2_strategies import (
    TrendPullbackV2Strategy,
    BreakoutConfirmV2Strategy,
    MomentumRSV2Strategy,
    MeanReversionV2Strategy,
)


def test_frozen_v2_strategy_hashes():
    """Verify exact SHA256 hashes of all four frozen V2 strategy configurations."""
    hashes = {
        TrendPullbackV2Strategy(): "5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523",
        BreakoutConfirmV2Strategy(): "f482e1baa26bdc15e7b589ff3baa06550a314f911db667062f553c029c4da213",
        MomentumRSV2Strategy(): "8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d",
        MeanReversionV2Strategy(): "8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82",
    }
    for strat, expected_hash in hashes.items():
        assert strat.config_hash == expected_hash, f"Hash mismatch for {strat.name}"


def test_development_firewall_raises_databoundaryviolationerror():
    """Verify that DataPortal/firewall guard raises DataBoundaryViolationError for dates beyond DEVELOPMENT."""
    fw = DevelopmentDataFirewall()

    # Allowed DEVELOPMENT date
    fw.validate_date(date(2020, 5, 15))
    assert fw.development_access_count == 1
    assert fw.validation_access_count == 0
    assert fw.final_test_access_count == 0

    # Blocked VALIDATION date
    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2022, 1, 1))

    # Blocked FINAL TEST date
    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2024, 7, 1))

    assert fw.validation_access_count == 1
    assert fw.final_test_access_count == 1


def test_gate_provenance_audit_classifications():
    """Verify that gate criteria provenance classifications are documented strictly from evidence."""
    audits = GateProvenanceAuditor.audit_all()
    audit_dict = {a.metric_name: a for a in audits}

    assert audit_dict["win_rate"].classification == GateProvenanceClassification.PREDECLARED_HEURISTIC
    assert audit_dict["profit_factor"].classification == GateProvenanceClassification.PREDECLARED_AND_JUSTIFIED
    assert audit_dict["expectancy_r"].classification == GateProvenanceClassification.PREDECLARED_AND_JUSTIFIED
    assert audit_dict["semester_concentration"].classification == GateProvenanceClassification.PREDECLARED_AND_JUSTIFIED
    assert audit_dict["max_drawdown"].classification == GateProvenanceClassification.PREDECLARED_HEURISTIC


def test_m3b3_decision_policy_deterministic_rules():
    """Verify M3B3DecisionPolicy v1.0 produces deterministic decisions from evidence packages."""

    # 1. Structurally negative gross edge -> ABANDON_FAMILY
    pkg_neg_gross = StrategyEvidencePackage(
        strategy_id="test_neg",
        strategy_name="Negative Gross Test",
        config_hash="abc",
        executed_trades=100,
        gross_pnl=Decimal("-50000.00"),
        explicit_costs=Decimal("20000.00"),
        net_pnl=Decimal("-70000.00"),
        total_return_pct=-7.0,
        profit_factor=0.6,
        win_rate=20.0,
        expectancy_r=-0.5,
        positive_years_count=0,
        total_years_count=5,
        best_year_pnl_share=0.0,
        yearly_classification=YearlyStabilityClassification.CONSISTENTLY_NEGATIVE,
        net_pnl_ex_top1=Decimal("-75000.00"),
        net_pnl_ex_top3=Decimal("-85000.00"),
        net_pnl_ex_top5=Decimal("-95000.00"),
        outlier_classification=OutlierDependenceClassification.DISTRIBUTED_EDGE,
        scenario_a_net_pnl=Decimal("-70000.00"),
        scenario_b_net_pnl=Decimal("-50000.00"),
        scenario_c_net_pnl=Decimal("-75000.00"),
        scenario_d_net_pnl=Decimal("-85000.00"),
        cost_classification=CostRobustnessClassification.NEGATIVE_BEFORE_FRICTION,
    )
    decision1, _, _ = M3B3DecisionPolicy.evaluate(pkg_neg_gross)
    assert decision1 == DecisionStatus.ABANDON_FAMILY

    # 2. Positive gross edge eroded by friction with outlier dependence -> ONE_FINAL_HYPOTHESIS_REVISION_ALLOWED
    pkg_revision = StrategyEvidencePackage(
        strategy_id="test_rev",
        strategy_name="Revision Test",
        config_hash="def",
        executed_trades=300,
        gross_pnl=Decimal("100000.00"),
        explicit_costs=Decimal("50000.00"),
        net_pnl=Decimal("50000.00"),
        total_return_pct=5.0,
        profit_factor=1.1,
        win_rate=11.0,
        expectancy_r=0.1,
        positive_years_count=3,
        total_years_count=5,
        best_year_pnl_share=0.4,
        yearly_classification=YearlyStabilityClassification.BROADLY_STABLE,
        net_pnl_ex_top1=Decimal("30000.00"),
        net_pnl_ex_top3=Decimal("-5000.00"),
        net_pnl_ex_top5=Decimal("-15000.00"),
        outlier_classification=OutlierDependenceClassification.OUTLIER_DEPENDENT,
        scenario_a_net_pnl=Decimal("50000.00"),
        scenario_b_net_pnl=Decimal("100000.00"),
        scenario_c_net_pnl=Decimal("20000.00"),
        scenario_d_net_pnl=Decimal("-10000.00"),
        cost_classification=CostRobustnessClassification.FRICTION_SENSITIVE,
    )
    decision2, _, _ = M3B3DecisionPolicy.evaluate(pkg_revision)
    assert decision2 == DecisionStatus.ONE_FINAL_HYPOTHESIS_REVISION_ALLOWED
