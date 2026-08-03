"""Public Research Client for TradeCraft Quantitative Platform."""

from datetime import date
from typing import Any

from tradecraft.research.alpha_library import AlphaLibrary, AlphaSourceRecord
from tradecraft.research.benchmark_suite import BenchmarkSuite
from tradecraft.research.experiment_budget_manager import (
    ExperimentBudgetManager,
)
from tradecraft.research.experiment_comparator import ComparisonSummary, ExperimentComparator
from tradecraft.research.experiment_registry import ExperimentRecord, ExperimentRegistry
from tradecraft.research.feature_registry import FeatureDefinition, FeatureRegistry
from tradecraft.research.feature_store import FeatureStore
from tradecraft.research.hypothesis_admission_gate import (
    AdmissionCheckResult,
    HypothesisAdmissionGate,
)
from tradecraft.research.hypothesis_registry import HypothesisRecord, HypothesisRegistry
from tradecraft.research.novelty_scoring_engine import NoveltyReport, NoveltyScoringEngine
from tradecraft.universe.historical_membership import HistoricalMembershipEngine
from tradecraft.universe.security_master import Security, SecurityMaster
from tradecraft.universe.universe_api import UniverseAPI
from tradecraft.universe.universe_registry import UniverseRegistry


class ResearchClient:
    """Public client exposing research platform & framework capabilities to notebooks & scripts."""

    def __init__(self) -> None:
        self.alpha_library = AlphaLibrary()
        self.admission_gate = HypothesisAdmissionGate()
        self.novelty_engine = NoveltyScoringEngine()
        self.budget_manager = ExperimentBudgetManager()
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

    def list_alpha_sources(self) -> list[AlphaSourceRecord]:
        """List all 20 pre-registered institutional alpha sources."""
        return self.alpha_library.list_alpha_sources()

    def get_alpha_source(self, alpha_id: str) -> AlphaSourceRecord | None:
        """Retrieve alpha source metadata by alpha_id (e.g. 'ALPHA-001')."""
        return self.alpha_library.get_alpha_source(alpha_id)

    def validate_hypothesis_admission(self, hypothesis: HypothesisRecord) -> AdmissionCheckResult:
        """Validate hypothesis against the 8-point admission checklist."""
        return self.admission_gate.evaluate_hypothesis(hypothesis)

    def check_hypothesis_novelty(self, hypothesis: HypothesisRecord) -> NoveltyReport:
        """Check hypothesis similarity against abandoned Graveyard lineages."""
        return self.novelty_engine.evaluate_novelty(hypothesis)

    def list_registered_features(self) -> list[FeatureDefinition]:
        """List all pre-registered features in the platform."""
        return self.feature_registry.list_features()

    def register_hypothesis(self, record: HypothesisRecord) -> str:
        """Pre-register a research hypothesis prior to execution."""
        # Enforce admission check & novelty check before registration
        admission = self.validate_hypothesis_admission(record)
        if not admission.is_admitted:
            raise ValueError(f"HYPOTHESIS ADMISSION REJECTED: {', '.join(admission.rejection_reasons)}")

        novelty = self.check_hypothesis_novelty(record)
        if not novelty.is_sufficiently_novel:
            raise ValueError(f"HYPOTHESIS NOVELTY REJECTED: {novelty.explanation}")

        return self.hypothesis_registry.register_hypothesis(record)

    def list_hypotheses(self) -> list[HypothesisRecord]:
        """List all pre-registered hypotheses."""
        return self.hypothesis_registry.list_hypotheses()

    def register_experiment(self, record: ExperimentRecord) -> str:
        """Register an experiment run record."""
        self.budget_manager.consume_experiment_quota()
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
