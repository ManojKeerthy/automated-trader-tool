"""Unit tests for Milestone M3C.0 Research Cycle 1 Closure & Research Governance Baseline."""

from datetime import date
from pathlib import Path

import pytest

from tradecraft.research.firewall import DataBoundaryViolationError, DevelopmentDataFirewall
from tradecraft.research.m3c_0_governance import (
    GraveyardEnforcementGuard,
    LineageCollisionDetector,
    ResearchGovernanceError,
    ResearchGovernanceManager,
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
    assert LineageCollisionDetector.inspect_proposed_hypothesis(
        strategy_id="strat_new_concept",
        parameters={},
        rule_summary="A strategy based on RSI oversold and Donchian breakout.",
    ) is True

    assert LineageCollisionDetector.inspect_proposed_hypothesis(
        strategy_id="strat_novel_market_breadth",
        parameters={},
        rule_summary="A cross-sectional market breadth divergence model.",
    ) is False


def test_m3c_0_research_governance_state_json():
    """Verify that config/research_governance_state.json exists and reports CLOSED_NO_SURVIVOR."""
    state_file = Path("config/research_governance_state.json")
    assert state_file.exists(), "config/research_governance_state.json must exist"

    mgr = ResearchGovernanceManager(state_file)
    assert mgr.validate_governance_state() is True
    assert mgr.state["research_cycle_1_status"] == "CLOSED_NO_SURVIVOR"
    assert mgr.state["validation_status"] == "SEALED_UNTOUCHED"
    assert mgr.state["final_test_status"] == "SEALED_UNTOUCHED"
    assert len(mgr.state["abandoned_strategy_families"]) == 4


def test_m3c_0_documentation_suite_exists():
    """Verify that all required permanent documentation files exist in docs/research/."""
    docs_dir = Path("docs/research")
    required_files = [
        "START_HERE.md",
        "research_principles.md",
        "research_cycle_1_summary.md",
        "strategy_lineage_registry.md",
        "research_graveyard.md",
        "research_decision_log.md",
        "known_mistakes.md",
        "engineering_lessons.md",
        "backtesting_invariants.md",
        "research_methodology.md",
        "anti_overfitting_rules.md",
        "dataset_firewall.md",
        "gate_methodology_review.md",
        "future_research_questions.md",
        "universe_expansion_requirements.md",
        "research_roadmap.md",
        "glossary.md",
        "research_cycle_1_lessons.json",
    ]
    for fname in required_files:
        p = docs_dir / fname
        assert p.exists(), f"Missing required documentation artifact: {p}"

    adr_dir = docs_dir / "adr"
    required_adrs = [
        "ADR-001_why_t_plus_1_execution.md",
        "ADR-002_why_force_close_policy.md",
        "ADR-003_why_sha256_hypothesis_hashes.md",
        "ADR-004_why_immutable_graveyard.md",
        "ADR-005_why_three_datasets.md",
        "ADR-006_why_point_in_time_features.md",
    ]
    for adr in required_adrs:
        p = adr_dir / adr
        assert p.exists(), f"Missing required ADR: {p}"
