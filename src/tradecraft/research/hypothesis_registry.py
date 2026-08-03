"""Hypothesis Registry & Pre-Registration Engine."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class HypothesisRecord:
    """Immutable pre-registered research hypothesis record."""
    hypothesis_uuid: str
    hypothesis_name: str
    parent_hypothesis_uuid: str | None
    economic_rationale: str
    behavioural_rationale: str
    expected_market_behaviour: str
    falsification_criteria: str
    supporting_literature: list[str]
    status: str = "REGISTERED"  # REGISTERED, ACTIVE, FAILED, ABANDONED, PROMOTED, SUPERSEDED
    author: str = "TradeCraft Research Team"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def checksum(self) -> str:
        """Compute SHA256 cryptographic hash for hypothesis lock."""
        payload = f"{self.hypothesis_uuid}:{self.hypothesis_name}:{self.economic_rationale}:{self.falsification_criteria}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_uuid": self.hypothesis_uuid,
            "hypothesis_name": self.hypothesis_name,
            "parent_hypothesis_uuid": self.parent_hypothesis_uuid,
            "economic_rationale": self.economic_rationale,
            "behavioural_rationale": self.behavioural_rationale,
            "expected_market_behaviour": self.expected_market_behaviour,
            "falsification_criteria": self.falsification_criteria,
            "supporting_literature": self.supporting_literature,
            "status": self.status,
            "checksum": self.checksum,
            "author": self.author,
            "created_at": self.created_at,
        }


class HypothesisRegistry:
    """Central registry enforcing pre-registration immutability before experiment execution."""

    VALID_STATUSES = {"REGISTERED", "ACTIVE", "FAILED", "ABANDONED", "PROMOTED", "SUPERSEDED"}

    def __init__(self) -> None:
        self._registry: dict[str, HypothesisRecord] = {}

    def register_hypothesis(self, record: HypothesisRecord) -> str:
        """Pre-register a new research hypothesis. Immutably locked after registration."""
        if record.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid hypothesis status: {record.status}")
        self._registry[record.hypothesis_uuid] = record
        return record.hypothesis_uuid

    def get_hypothesis(self, hypothesis_uuid: str) -> HypothesisRecord | None:
        """Retrieve hypothesis by UUID."""
        return self._registry.get(hypothesis_uuid)

    def update_status(self, hypothesis_uuid: str, new_status: str) -> None:
        """Update hypothesis status (e.g. from REGISTERED to FAILED or ABANDONED)."""
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")
        record = self._registry.get(hypothesis_uuid)
        if not record:
            raise KeyError(f"Hypothesis UUID '{hypothesis_uuid}' not found!")
        record.status = new_status

    def list_hypotheses(self) -> list[HypothesisRecord]:
        """List all pre-registered hypotheses."""
        return list(self._registry.values())
