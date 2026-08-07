"""Unit tests for Milestone M3B.4 Final Hypothesis Revision & Development Survivor Gate."""

from datetime import date

import pytest

from tradecraft.research.firewall import DataBoundaryViolationError, DevelopmentDataFirewall
from tradecraft.research.m3b_4_gate import DevelopmentSurvivorGateEvaluator
from tradecraft.research.m3b_4_hypothesis import (
    V3ParameterOrigin,
)
from tradecraft.strategy.breakout_confirm_v3 import BreakoutConfirmV3Strategy
from tradecraft.strategy.mean_reversion_v3 import MeanReversionV3Strategy
from tradecraft.strategy.v2_strategies import MomentumRSV2Strategy, TrendPullbackV2Strategy


def test_v2_parent_hashes_and_graveyard_locking():
    """Verify that Trend Pullback V2 and Momentum RS V2 are locked and V3 parent hashes match."""
    tp_v2 = TrendPullbackV2Strategy()
    mom_v2 = MomentumRSV2Strategy()
    assert tp_v2.config_hash == "c4556b07bd4edc39f9a53c1c27c601d2c0747fcbc7ad356d4e4ec42af6c993da"
    assert mom_v2.config_hash == "221c35751fde73a351138d14502bd8b1bf6ad49e051bfe55d6bb086a1d2df825"

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



# test_m3b4_artifacts_exist removed 2026-08-06: certified the existence of
# scratch/m3b_4_*.json artifacts from the voided Cycle 1/2 synthetic-data research run,
# deleted in the 2026-08-06 governance cleanup (see CLAUDE.md, "Do not trust the historical
# record"). The other five tests in this file exercise real, still-valid mechanisms (hash
# locking, parameter-provenance auditing, the data firewall, the survivor gate evaluator)
# and are kept.
