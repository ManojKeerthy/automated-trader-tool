"""Experiment Explorer for UUID-based historical experiment navigation."""

from tradecraft.research.experiment_registry import ExperimentRecord, ExperimentRegistry


class ExperimentExplorer:
    """Searchable UUID-based experiment history explorer."""

    def __init__(self, registry: ExperimentRegistry):
        self.registry = registry

    def find_by_id(self, experiment_id: str) -> ExperimentRecord | None:
        """Find experiment record by exact UUID / ID."""
        return self.registry.get_experiment(experiment_id)

    def find_by_hypothesis(self, hypothesis_uuid: str) -> list[ExperimentRecord]:
        """Find experiment records linked to a specific hypothesis_uuid."""
        return [e for e in self.registry.list_experiments() if e.hypothesis_uuid == hypothesis_uuid]

    def find_by_universe(self, universe_version: str) -> list[ExperimentRecord]:
        """Find experiment records executed on a specific universe_version."""
        return [
            e for e in self.registry.list_experiments() if e.universe_version == universe_version
        ]
