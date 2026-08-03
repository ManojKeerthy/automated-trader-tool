"""Metadata Catalog for Institutional Data Platform Asset Management."""

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class CatalogAsset:
    """Institutional asset metadata record with dependency lineage."""
    uuid: str
    name: str
    asset_type: str  # UNIVERSE, DATASET, CORPORATE_ACTIONS, MEMBERSHIP, FEATURES, BACKTESTS, EXPERIMENTS, REPORTS
    version: str = "1.0.0"
    source: str = "TradeCraft Research Pipeline"
    owner: str = "TradeCraft Research Governance"
    dependencies: List[str] = field(default_factory=list)  # UUIDs of parent assets
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def checksum(self) -> str:
        """Compute SHA256 checksum of asset metadata."""
        payload = f"{self.uuid}:{self.name}:{self.version}:{self.asset_type}:{','.join(self.dependencies)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "asset_type": self.asset_type,
            "version": self.version,
            "source": self.source,
            "owner": self.owner,
            "dependencies": self.dependencies,
            "checksum": self.checksum,
            "created_at": self.created_at,
        }


class MetadataCatalog:
    """Catalog managing asset metadata records and dependency trees."""

    def __init__(self) -> None:
        self._assets: Dict[str, CatalogAsset] = {}

    def register_asset(self, asset: CatalogAsset) -> str:
        """Register an asset into the Metadata Catalog."""
        self._assets[asset.uuid] = asset
        return asset.uuid

    def get_asset(self, asset_uuid: str) -> Optional[CatalogAsset]:
        """Retrieve an asset by UUID."""
        return self._assets.get(asset_uuid)

    def list_assets(self, asset_type: Optional[str] = None) -> List[CatalogAsset]:
        """List registered assets, optionally filtered by asset_type."""
        if asset_type:
            return [a for a in self._assets.values() if a.asset_type.upper() == asset_type.upper()]
        return list(self._assets.values())
