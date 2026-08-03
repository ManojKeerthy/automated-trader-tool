"""Immutable Research Ledger for M3B.2.

Tracks all evaluated V2 strategy configurations, hashes, parent lineages, hypotheses, parameter origins,
evaluated phases, metrics exposed, outcomes, rejection reasons, and next permitted states.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ResearchLedgerEntry:
    experiment_id: str
    strategy_family: str
    strategy_id: str
    parent_strategy_id: str
    config_hash: str
    parameters: dict[str, Any]
    hypothesis_statement: str
    parameter_origins: list[dict[str, Any]]
    phase: str  # PHASE_A, PHASE_B, PHASE_C, PHASE_D_DEVELOPMENT, PHASE_D_ROBUSTNESS
    timestamp: str
    data_range_accessed: str  # DEVELOPMENT (2016-08-01 -> 2021-12-31)
    metrics_exposed: list[str]
    outcome_status: str
    rejection_reason: str
    next_permitted_state: str


class ImmutableResearchLedger:
    """Immutable Research Ledger maintaining audit trail for M3B.2."""

    def __init__(self, db_session: Session | None = None):
        self.db = db_session
        self.entries: list[ResearchLedgerEntry] = []

    def record_entry(self, entry: ResearchLedgerEntry) -> None:
        """Add entry to ledger."""
        self.entries.append(entry)
        logger.info(f"Ledger recorded entry for {entry.strategy_id} ({entry.config_hash[:12]}...) under phase {entry.phase}: {entry.outcome_status}")

    def export_json(self, file_path: str) -> None:
        """Export ledger entries to JSON file."""
        data = [asdict(e) for e in self.entries]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Research ledger exported to {file_path}")
