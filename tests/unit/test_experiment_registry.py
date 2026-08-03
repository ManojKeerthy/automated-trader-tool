"""Unit tests for ExperimentRegistry."""

import pytest
from tradecraft.research.experiment_registry import EnvironmentMetadata, ExperimentRecord, ExperimentRegistry


def test_experiment_registry_and_reproducibility():
    reg = ExperimentRegistry()
    env = EnvironmentMetadata()
    record = ExperimentRecord(
        experiment_id="exp-1",
        hypothesis_uuid="hypo-1",
        strategy_version="v1.0",
        feature_versions=["1.0.0"],
        dataset_version="v1",
        universe_version="NIFTY50",
        environment=env,
    )
    reg.register_experiment(record)
    assert len(record.execution_hash) == 64
    assert reg.get_experiment("exp-1") == record
