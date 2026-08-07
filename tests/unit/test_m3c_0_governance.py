"""Unit tests for Milestone M3C.0 Research Cycle 1 Closure & Research Governance Baseline."""

from datetime import date

import pytest

from tradecraft.research.firewall import DataBoundaryViolationError, DevelopmentDataFirewall
from tradecraft.research.m3c_0_governance import (
    GraveyardEnforcementGuard,
    LineageCollisionDetector,
    ResearchGovernanceError,
)


def test_m3c_0_dataset_firewall_enforcement():
    """Verify that DevelopmentDataFirewall blocks access to Validation and Final Test dates."""
    fw = DevelopmentDataFirewall()
    fw.validate_date(date(2020, 1, 15))  # Allowed

    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2022, 1, 1))

    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2024, 7, 1))

    assert fw.validation_access_count == 1
    assert fw.final_test_access_count == 1


def test_m3c_0_graveyard_enforcement_guard():
    """Verify that GraveyardEnforcementGuard blocks registration/execution of abandoned strategy families."""
    abandoned_ids = [
        "strat_trend_pullback_v4",
        "strat_momentum_rs_v3",
        "strat_breakout_confirm_v4",
        "strat_mean_reversion_v4",
    ]
    for strat_id in abandoned_ids:
        with pytest.raises(ResearchGovernanceError):
            GraveyardEnforcementGuard.check_strategy_id(strat_id)


def test_m3c_0_lineage_collision_detector():
    """Verify that LineageCollisionDetector flags suspect rule patterns matching abandoned lineages."""
    assert (
        LineageCollisionDetector.inspect_proposed_hypothesis(
            strategy_id="strat_new_concept",
            parameters={},
            rule_summary="A strategy based on RSI oversold and Donchian breakout.",
        )
        is True
    )

    assert (
        LineageCollisionDetector.inspect_proposed_hypothesis(
            strategy_id="strat_novel_market_breadth",
            parameters={},
            rule_summary="A cross-sectional market breadth divergence model.",
        )
        is False
    )



# test_m3c_0_research_governance_state_json and test_m3c_0_documentation_suite_exists
# removed 2026-08-06. Both certified the PRE-AUDIT state as correct: the first asserted
# research_cycle_1_status == "CLOSED_NO_SURVIVOR" and validation/final_test_status ==
# "SEALED_UNTOUCHED", claims the 2026-08-06 audit found false (Cycle 1 ran on synthetic
# data, so status is now correctly VOID_SYNTHETIC_DATA; "SEALED_UNTOUCHED" was vacuous since
# the final-test range held zero rows, now correctly POPULATED_SEALED with real data). The
# second required docs/research/research_cycle_1_summary.md and research_cycle_1_lessons.json
# to exist - both correctly deleted in the same cleanup, since they documented conclusions
# drawn from fabricated prices. Keeping either test passing would mean reverting real
# corrections back to false claims, or resurrecting deleted fictional documentation. See
# CLAUDE.md, "Do not trust the historical record", and PROJECT_STATUS.md section 2. The
# other three tests in this file (firewall, graveyard guard, lineage collision detector)
# exercise real, still-valid mechanisms and are kept. (The removed test also checked for
# ADR-00N_why_*.md files under docs/adr/ - also void, from the same methodology cycle; the
# ADRs that actually exist today are numbered/named differently and cover real architecture
# decisions, e.g. ADR-008-human-approval-workflow.md.)
