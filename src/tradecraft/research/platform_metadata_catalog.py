"""Platform Metadata Catalog for asset dependency tracking."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PlatformAssetNode:
    """Dependency graph node representing a research asset."""

    node_id: str
    name: str
    asset_type: str  # UNIVERSE, DATASET, FEATURE, HYPOTHESIS, EXPERIMENT, STRATEGY, REPORT, ARTIFACT, DECISION
    version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def checksum(self) -> str:
        payload = f"{self.node_id}:{self.name}:{self.asset_type}:{self.version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "version": self.version,
            "dependencies": self.dependencies,
            "checksum": self.checksum,
            "created_at": self.created_at,
        }


class PlatformMetadataCatalog:
    """Asset dependency catalog connecting Universe -> Dataset -> Features -> Experiments -> Reports."""

    def __init__(self) -> None:
        self._nodes: dict[str, PlatformAssetNode] = {}

    def register_node(self, node: PlatformAssetNode) -> str:
        self._nodes[node.node_id] = node
        return node.node_id

    def get_node(self, node_id: str) -> PlatformAssetNode | None:
        return self._nodes.get(node_id)

    def list_nodes(self) -> list[PlatformAssetNode]:
        return list(self._nodes.values())
