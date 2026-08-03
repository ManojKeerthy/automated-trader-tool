"""Feature Store for versioned, cached, reusable feature storage."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CachedFeatureRecord:
    """Record container for calculated and cached feature values."""
    feature_name: str
    feature_version: str
    universe_version: str
    dataset_version: str
    security_uuid: str
    observation_date: str
    value: float
    checksum: str
    computed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class FeatureStore:
    """Versioned, cached feature storage engine."""

    def __init__(self) -> None:
        self._cache: dict[str, CachedFeatureRecord] = {}

    def get_cache_key(
        self,
        feature_name: str,
        security_uuid: str,
        observation_date: str,
        feature_version: str = "1.0.0",
        dataset_version: str = "v1",
    ) -> str:
        payload = f"{feature_name}:{feature_version}:{dataset_version}:{security_uuid}:{observation_date}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_feature_value(
        self,
        feature_name: str,
        security_uuid: str,
        observation_date: str,
        feature_version: str = "1.0.0",
        dataset_version: str = "v1",
    ) -> float | None:
        """Fetch cached feature value if available."""
        key = self.get_cache_key(feature_name, security_uuid, observation_date, feature_version, dataset_version)
        record = self._cache.get(key)
        return record.value if record else None

    def store_feature_value(
        self,
        feature_name: str,
        security_uuid: str,
        observation_date: str,
        value: float,
        feature_version: str = "1.0.0",
        universe_version: str = "1.0.0",
        dataset_version: str = "v1",
    ) -> str:
        """Store computed feature value in cache."""
        key = self.get_cache_key(feature_name, security_uuid, observation_date, feature_version, dataset_version)
        record = CachedFeatureRecord(
            feature_name=feature_name,
            feature_version=feature_version,
            universe_version=universe_version,
            dataset_version=dataset_version,
            security_uuid=security_uuid,
            observation_date=observation_date,
            value=value,
            checksum=key,
        )
        self._cache[key] = record
        return key
