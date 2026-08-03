"""Research Dashboard Metadata Layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DashboardMetadataSnapshot:
    """Metadata layer snapshot for quantitative research dashboard UI."""
    active_research_cycle: str = "CYCLE_1"
    completed_milestones: list[str] = field(default_factory=lambda: ["M3A", "M3B", "M3C.0", "M3C.1", "M3C.2", "M3C.3"])
    abandoned_families_count: int = 4
    registered_hypotheses_count: int = 2
    registered_features_count: int = 12
    sealed_datasets: dict[str, str] = field(default_factory=lambda: {
        "VALIDATION": "2022-01-01 -> 2024-06-30 (SEALED)",
        "FINAL_TEST": "2024-07-01 -> 2026-07-28 (SEALED)",
    })
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_research_cycle": self.active_research_cycle,
            "completed_milestones": self.completed_milestones,
            "abandoned_families_count": self.abandoned_families_count,
            "registered_hypotheses_count": self.registered_hypotheses_count,
            "registered_features_count": self.registered_features_count,
            "sealed_datasets": self.sealed_datasets,
            "generated_at": self.generated_at,
        }
