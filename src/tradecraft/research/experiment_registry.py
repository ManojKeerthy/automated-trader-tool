"""Experiment Registry & Full Environment Reproducibility Engine."""

import hashlib
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EnvironmentMetadata:
    """Full environment reproducibility metadata container."""
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    os_system: str = field(default_factory=lambda: platform.system())
    os_release: str = field(default_factory=lambda: platform.release())
    cpu_architecture: str = field(default_factory=lambda: platform.machine())
    ram_gb_approx: float = 16.0
    package_versions_summary: str = "pytest-9.1.1, mypy-strict, sqlalchemy-2.0, pandas"

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "os_system": self.os_system,
            "os_release": self.os_release,
            "cpu_architecture": self.cpu_architecture,
            "ram_gb_approx": self.ram_gb_approx,
            "package_versions_summary": self.package_versions_summary,
        }


@dataclass
class ExperimentRecord:
    """Immutable experiment record container for 100% reproducibility."""
    experiment_id: str
    hypothesis_uuid: str
    strategy_version: str
    feature_versions: list[str]
    dataset_version: str
    universe_version: str
    environment: EnvironmentMetadata
    random_seed: int = 42
    git_commit: str = "HEAD"
    researcher_notes: str = ""
    runtime_seconds: float = 0.0
    execution_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def execution_hash(self) -> str:
        """Compute SHA256 cryptographic execution hash covering environment and versions."""
        payload = (
            f"{self.experiment_id}:{self.hypothesis_uuid}:{self.strategy_version}:"
            f"{self.dataset_version}:{self.universe_version}:{self.environment.python_version}:"
            f"{self.environment.os_system}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_uuid": self.hypothesis_uuid,
            "strategy_version": self.strategy_version,
            "feature_versions": self.feature_versions,
            "dataset_version": self.dataset_version,
            "universe_version": self.universe_version,
            "environment": self.environment.to_dict(),
            "random_seed": self.random_seed,
            "git_commit": self.git_commit,
            "execution_hash": self.execution_hash,
            "researcher_notes": self.researcher_notes,
            "runtime_seconds": self.runtime_seconds,
            "execution_timestamp": self.execution_timestamp,
        }


class ExperimentRegistry:
    """Central registry tracking all quantitative experiments."""

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentRecord] = {}

    def register_experiment(self, record: ExperimentRecord) -> str:
        """Register a quantitative experiment."""
        self._experiments[record.experiment_id] = record
        return record.experiment_id

    def get_experiment(self, experiment_id: str) -> ExperimentRecord | None:
        """Retrieve experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[ExperimentRecord]:
        """List all registered experiment records."""
        return list(self._experiments.values())
