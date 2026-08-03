"""Public Research Client for TradeCraft Quantitative Platform."""

from datetime import date
from typing import Any

from tradecraft.research.benchmark_suite import BenchmarkSuite
from tradecraft.research.experiment_comparator import ComparisonSummary, ExperimentComparator
from tradecraft.research.experiment_registry import ExperimentRecord, ExperimentRegistry
from tradecraft.research.feature_registry import FeatureDefinition, FeatureRegistry
from tradecraft.research.feature_store import FeatureStore
from tradecraft.research.hypothesis_registry import HypothesisRecord, HypothesisRegistry
from tradecraft.universe.historical_membership import HistoricalMembershipEngine
from tradecraft.universe.security_master import Security, SecurityMaster
from tradecraft.universe.universe_api import UniverseAPI
from tradecraft.universe.universe_registry import UniverseRegistry


class ResearchClient:
    """Public client exposing research platform capabilities to notebooks & scripts."""

    def __init__(self) -> None:
        self.feature_registry = FeatureRegistry()
        self.feature_store = FeatureStore()
        self.hypothesis_registry = HypothesisRegistry()
        self.experiment_registry = ExperimentRegistry()
        self.benchmark_suite = BenchmarkSuite()
        self.comparator = ExperimentComparator()
        self.security_master = SecurityMaster()
        self.universe_registry = UniverseRegistry()
        self.membership_engine = HistoricalMembershipEngine()
        self.universe_api = UniverseAPI(self.security_master, self.universe_registry, self.membership_engine)

    def list_registered_features(self) -> list[FeatureDefinition]:
        """List all pre-registered features in the platform."""
        return self.feature_registry.list_features()

    def register_hypothesis(self, record: HypothesisRecord) -> str:
        """Pre-register a research hypothesis prior to execution."""
        return self.hypothesis_registry.register_hypothesis(record)

    def list_hypotheses(self) -> list[HypothesisRecord]:
        """List all pre-registered hypotheses."""
        return self.hypothesis_registry.list_hypotheses()

    def register_experiment(self, record: ExperimentRecord) -> str:
        """Register an experiment run record."""
        return self.experiment_registry.register_experiment(record)

    def compare_experiments(self, experiments_data: list[dict[str, Any]]) -> ComparisonSummary:
        """Compare multiple experiments quantitatively side-by-side."""
        return self.comparator.compare_experiments(experiments_data)

    def get_universe_constituents(self, universe_id: str, query_date: date) -> list[Security]:
        """Fetch Point-in-Time universe constituents."""
        return self.universe_api.get_constituents(universe_id, query_date)


class TradeCraftSDK(ResearchClient):
    """Alias for ResearchClient."""
    pass
