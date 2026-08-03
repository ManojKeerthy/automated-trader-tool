"""Universe Registry & Dataset Versioning for Point-in-Time Research Architecture."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UniverseDefinition:
    """Explicit definition and versioning metadata for an equity universe."""
    universe_id: str  # e.g., "NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500", "CUSTOM"
    name: str
    version: str = "1.0.0"
    dataset_version: str = "v1"
    membership_version: str = "1.0.0"
    corporate_action_version: str = "1.0.0"
    security_master_version: str = "1.0.0"
    methodology: str = "Market Capitalisation Rank"
    source: str = "NSE Official Indices"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def checksum(self) -> str:
        """Compute SHA256 cryptographic checksum of universe metadata for reproducibility."""
        payload = f"{self.universe_id}:{self.version}:{self.dataset_version}:{self.membership_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe_id": self.universe_id,
            "name": self.name,
            "version": self.version,
            "dataset_version": self.dataset_version,
            "membership_version": self.membership_version,
            "corporate_action_version": self.corporate_action_version,
            "security_master_version": self.security_master_version,
            "methodology": self.methodology,
            "source": self.source,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UniverseRegistry:
    """Central registry managing supported universes and dataset versions."""

    SUPPORTED_UNIVERSES = ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500", "CUSTOM"]

    def __init__(self) -> None:
        self._universes: dict[str, UniverseDefinition] = {}
        self._initialize_canonical_universes()

    def _initialize_canonical_universes(self) -> None:
        """Initialize standard NIFTY index universe definitions."""
        for uid in self.SUPPORTED_UNIVERSES:
            self._universes[uid] = UniverseDefinition(
                universe_id=uid,
                name=f"NSE {uid} Index Universe",
                version="1.0.0",
                dataset_version="v1",
                methodology=f"Official NSE {uid} constituent criteria",
            )

    def register_universe(self, definition: UniverseDefinition) -> None:
        """Register or update a universe definition."""
        self._universes[definition.universe_id] = definition

    def get_universe(self, universe_id: str) -> UniverseDefinition | None:
        """Retrieve universe definition by universe_id."""
        return self._universes.get(universe_id.upper())

    def list_universes(self) -> list[UniverseDefinition]:
        """List all registered universe definitions."""
        return list(self._universes.values())
