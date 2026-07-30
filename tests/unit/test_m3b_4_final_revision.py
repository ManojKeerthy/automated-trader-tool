"""Unit tests for Milestone M3B.4 Final Hypothesis Revision & Development Survivor Gate."""

import json
from datetime import date
from pathlib import Path
import pytest

from tradecraft.research.splits import DEVELOPMENT_SPLIT, VALIDATION_SPLIT, FINAL_TEST_SPLIT
from tradecraft.research.firewall import DevelopmentDataFirewall, DataBoundaryViolationError
from tradecraft.research.m3b_4_hypothesis import (
    V3ParameterOrigin,
    V3HypothesisPreRegistration,
    V3HypothesisRegistry,
)
from tradecraft.research.m3b_4_gate import DevelopmentSurvivorGateEvaluator
from tradecraft.strategy.v2_strategies import TrendPullbackV2Strategy, MomentumRSV2Strategy
from tradecraft.strategy.breakout_confirm_v3 import BreakoutConfirmV3Strategy
from tradecraft.strategy.mean_reversion_v3 import MeanReversionV3Strategy


def test_v2_parent_hashes_and_graveyard_locking():
    """Verify that Trend Pullback V2 and Momentum RS V2 are locked and V3 parent hashes match."""
    tp_v2 = TrendPullbackV2Strategy()
    mom_v2 = MomentumRSV2Strategy()
    assert tp_v2.config_hash == "5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523"
    assert mom_v2.config_hash == "8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d"

    bo_v3 = BreakoutConfirmV3Strategy()
    mr_v3 = MeanReversionV3Strategy()
    assert bo_v3.parent_strategy_id == "strat_breakout_confirm_v2"
    assert mr_v3.parent_strategy_id == "strat_mean_reversion_v2"


def test_parameter_selection_provenance_audit_passes():
    """Verify that Parameter Selection Provenance Audit succeeds when alternatives_tested=False and pnl_used_to_select=False."""
    param_origin = V3ParameterOrigin(
        parameter_name="confirmation_sessions",
        v2_value=1,
        v3_value=2,
        provenance="ECONOMICALLY_DERIVED",
        alternatives_tested=False,
        pnl_used_to_select=False,
        justification="2-session Close confirmation ensures institutional trend commitment.",
    )
    assert param_origin.audit() == "PASS"


def test_parameter_selection_provenance_audit_fails_on_optimization():
    """Verify that Parameter Selection Provenance Audit raises error if alternatives_tested=True or pnl_used_to_select=True."""
    opt_param1 = V3ParameterOrigin(
        parameter_name="max_consolidation_pct",
        v2_value=0.20,
        v3_value=0.15,
        provenance="POST_HOC_DIAGNOSTIC_MOTIVATED",
        alternatives_tested=True,  # VIOLATION
        pnl_used_to_select=False,
        justification="Tested 10%, 12%, 15% and picked 15%.",
    )
    assert "OPTIMISED_ON_DEVELOPMENT" in opt_param1.audit()

    opt_param2 = V3ParameterOrigin(
        parameter_name="rsi_oversold",
        v2_value=40.0,
        v3_value=35.0,
        provenance="POST_HOC_DIAGNOSTIC_MOTIVATED",
        alternatives_tested=False,
        pnl_used_to_select=True,  # VIOLATION
        justification="Inspected P&L to pick 35.",
    )
    assert "OPTIMISED_ON_DEVELOPMENT" in opt_param2.audit()


def test_development_firewall_m3b4():
    """Verify firewall enforcement during M3B.4."""
    fw = DevelopmentDataFirewall()
    fw.validate_date(date(2021, 6, 1))

    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2022, 1, 1))

    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2024, 7, 1))

    assert fw.validation_access_count == 1
    assert fw.final_test_access_count == 1


def test_development_survivor_gate_evaluator():
    """Verify strict mathematical gate pass/fail evaluation."""
    # Strategy failing win_rate gate (e.g. 15% < 35%) -> ABANDON_FAMILY
    res_fail = DevelopmentSurvivorGateEvaluator.evaluate(
        win_rate=15.0,
        profit_factor=1.45,
        expectancy_r=0.32,
        max_drawdown_pct=14.0,
        semester_concentration_pct=25.0,
    )
    assert res_fail["overall_gate_result"] == "FAIL"
    assert res_fail["final_decision"] == "ABANDON_FAMILY"
    assert res_fail["validation_status"] == "BLOCKED"

    # Strategy passing all gates -> DEVELOPMENT_SURVIVOR
    res_pass = DevelopmentSurvivorGateEvaluator.evaluate(
        win_rate=38.0,
        profit_factor=1.45,
        expectancy_r=0.32,
        max_drawdown_pct=14.0,
        semester_concentration_pct=25.0,
    )
    assert res_pass["overall_gate_result"] == "PASS"
    assert res_pass["final_decision"] == "DEVELOPMENT_SURVIVOR"
    assert res_pass["validation_status"] == "ELIGIBLE_FOR_FUTURE_VALIDATION"


def test_m3b4_artifacts_exist():
    """Verify that all required M3B.4 artifacts exist."""
    assert Path("scratch/m3b_4_v3_hypothesis_registry.json").exists()
    assert Path("scratch/m3b_4_signal_viability.json").exists()
    assert Path("scratch/m3b_4_development_results.json").exists()
    assert Path("scratch/m3b_4_robustness_diagnostics.json").exists()
