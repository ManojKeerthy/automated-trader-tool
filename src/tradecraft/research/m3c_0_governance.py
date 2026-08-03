"""Programmatic Research Governance and Lineage Protection Module for M3C.0."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ResearchGovernanceError(Exception):
    """Raised when a research governance or graveyard rule is violated."""
    pass


class ResearchGovernanceManager:
    """Manages machine-readable research governance state."""

    def __init__(self, config_path: Path = Path("config/research_governance_state.json")):
        self.config_path = config_path
        self.state = self.load_state()

    def load_state(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Governance state file not found at {self.config_path}")
        with open(self.config_path) as f:
            data = json.load(f)
        return dict(data)

    def validate_governance_state(self) -> bool:
        assert self.state["research_cycle_1_status"] == "CLOSED_NO_SURVIVOR"
        assert self.state["validation_status"] == "SEALED_UNTOUCHED"
        assert self.state["final_test_status"] == "SEALED_UNTOUCHED"
        assert len(self.state["abandoned_strategy_families"]) == 4
        assert len(self.state["active_strategy_families"]) == 0
        logger.info("RESEARCH GOVERNANCE STATE VALIDATED: Cycle 1 CLOSED_NO_SURVIVOR, Validation SEALED.")
        return True


class GraveyardEnforcementGuard:
    """Enforces graveyard immutability. Prevents registration/execution of abandoned lineages."""

    ABANDONED_PREFIXES = {
        "strat_trend_pullback",
        "strat_momentum_rs",
        "strat_breakout_confirm",
        "strat_mean_reversion",
    }

    @classmethod
    def check_strategy_id(cls, strategy_id: str) -> None:
        for prefix in cls.ABANDONED_PREFIXES:
            if strategy_id.startswith(prefix):
                raise ResearchGovernanceError(
                    f"GRAVEYARD VIOLATION: Strategy '{strategy_id}' belongs to abandoned family lineage '{prefix}'! "
                    "Abandoned families are permanently locked in the Research Graveyard."
                )


class LineageCollisionDetector:
    """Detects minor parameter tweaks that disguise retries of abandoned strategy lineages."""

    SUSPECT_RULE_PATTERNS = [
        ("rsi", "oversold"),
        ("donchian", "breakout"),
        ("sma50", "pullback"),
        ("relative_strength", "momentum"),
    ]

    @classmethod
    def inspect_proposed_hypothesis(cls, strategy_id: str, parameters: dict[str, Any], rule_summary: str) -> bool:
        # Check strategy ID prefix first
        try:
            GraveyardEnforcementGuard.check_strategy_id(strategy_id)
        except ResearchGovernanceError as e:
            logger.error(f"Lineage Collision Detected: {e}")
            return True

        summary_lower = rule_summary.lower()
        for term1, term2 in cls.SUSPECT_RULE_PATTERNS:
            if term1 in summary_lower and term2 in summary_lower:
                logger.warning(
                    f"LINEAGE COLLISION WARNING: Proposed rule summary contains suspect terms ({term1}, {term2}) "
                    "matching abandoned Cycle 1 lineages! Requires explicit Lineage Distinction Audit."
                )
                return True
        return False
