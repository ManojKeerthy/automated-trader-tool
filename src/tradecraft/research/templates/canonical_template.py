"""Canonical Experiment Template for repeatable quantitative research."""

import uuid
from dataclasses import dataclass

from tradecraft.research.experiment_registry import EnvironmentMetadata, ExperimentRecord


@dataclass
class CanonicalExperimentConfig:
    hypothesis_uuid: str
    strategy_version: str
    universe_id: str = "NIFTY50"
    dataset_version: str = "v1"
    feature_versions: list[str] = None  # type: ignore[assignment]
    researcher_notes: str = ""

    def __post_init__(self) -> None:
        if self.feature_versions is None:
            self.feature_versions = ["1.0.0"]


class CanonicalExperimentTemplate:
    """Standardized template for creating repeatable experiment records."""

    @staticmethod
    def create_experiment_record(config: CanonicalExperimentConfig) -> ExperimentRecord:
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        env = EnvironmentMetadata()
        return ExperimentRecord(
            experiment_id=exp_id,
            hypothesis_uuid=config.hypothesis_uuid,
            strategy_version=config.strategy_version,
            feature_versions=config.feature_versions,
            dataset_version=config.dataset_version,
            universe_version=config.universe_id,
            environment=env,
            researcher_notes=config.researcher_notes,
        )
