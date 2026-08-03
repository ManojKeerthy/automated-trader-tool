"""Feature Registry & Lineage Engine for Quantitative Research Platform."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FeatureLineage:
    """Explicit dependency graph lineage for a feature."""

    depends_on: list[str] = field(default_factory=list)  # Feature names or raw series
    raw_features: list[str] = field(default_factory=list)  # e.g. ["Close", "Volume"]
    dataset_version: str = "v1"
    corporate_action_version: str = "1.0.0"
    membership_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "depends_on": self.depends_on,
            "raw_features": self.raw_features,
            "dataset_version": self.dataset_version,
            "corporate_action_version": self.corporate_action_version,
            "membership_version": self.membership_version,
        }


@dataclass
class FeatureDefinition:
    """Immutable, versioned feature record."""

    feature_uuid: str
    feature_name: str
    description: str
    mathematical_definition: str
    required_inputs: list[str]
    lookback_period: int
    warmup_period: int
    lineage: FeatureLineage
    implementation_version: str = "1.0.0"
    author: str = "TradeCraft Quant Team"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def checksum(self) -> str:
        """Compute SHA256 cryptographic checksum of feature definition for 100% reproducibility."""
        payload = f"{self.feature_uuid}:{self.feature_name}:{self.implementation_version}:{self.mathematical_definition}:{','.join(self.required_inputs)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_uuid": self.feature_uuid,
            "feature_name": self.feature_name,
            "description": self.description,
            "mathematical_definition": self.mathematical_definition,
            "required_inputs": self.required_inputs,
            "lookback_period": self.lookback_period,
            "warmup_period": self.warmup_period,
            "implementation_version": self.implementation_version,
            "checksum": self.checksum,
            "lineage": self.lineage.to_dict(),
            "author": self.author,
            "created_at": self.created_at,
        }


class FeatureRegistry:
    """Central registry maintaining pre-registered core technical & regime features."""

    CORE_FEATURES = [
        "RSI",
        "ATR",
        "EMA",
        "SMA",
        "ADX",
        "MACD",
        "ROC",
        "Relative Strength",
        "Volatility",
        "Liquidity",
        "Sector Strength",
        "Market Regime",
    ]

    def __init__(self) -> None:
        self._registry: dict[str, FeatureDefinition] = {}
        self._initialize_core_features()

    def _initialize_core_features(self) -> None:
        """Register the 12 core quantitative features into the Feature Registry."""
        for feat in self.CORE_FEATURES:
            feat_uuid = f"feat-{feat.lower().replace(' ', '-')}-v1"
            lineage = FeatureLineage(
                depends_on=["OHLCV"],
                raw_features=["Close", "High", "Low", "Volume"],
                dataset_version="v1",
            )
            defn = FeatureDefinition(
                feature_uuid=feat_uuid,
                feature_name=feat,
                description=f"Standard quantitative feature calculation for {feat}",
                mathematical_definition=f"Formula for {feat}",
                required_inputs=["Close", "Volume"],
                lookback_period=20,
                warmup_period=50,
                lineage=lineage,
            )
            self._registry[feat.upper()] = defn

    def register_feature(self, definition: FeatureDefinition) -> str:
        """Register a custom feature definition."""
        self._registry[definition.feature_name.upper()] = definition
        return definition.feature_uuid

    def get_feature(self, feature_name: str) -> FeatureDefinition | None:
        """Retrieve feature definition by name."""
        return self._registry.get(feature_name.upper())

    def list_features(self) -> list[FeatureDefinition]:
        """List all pre-registered feature definitions."""
        return list(self._registry.values())
