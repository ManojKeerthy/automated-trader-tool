"""Experiment Budget Manager enforcing research quota limits."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ResearchCycleBudget:
    max_hypothesis_families: int = 5
    max_variants_per_family: int = 2
    max_development_experiments: int = 20
    current_hypothesis_families_count: int = 0
    current_experiments_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_hypothesis_families": self.max_hypothesis_families,
            "max_variants_per_family": self.max_variants_per_family,
            "max_development_experiments": self.max_development_experiments,
            "current_hypothesis_families_count": self.current_hypothesis_families_count,
            "current_experiments_count": self.current_experiments_count,
            "remaining_experiments": self.max_development_experiments - self.current_experiments_count,
        }


class ExperimentBudgetManager:
    """Enforces quota limits on hypothesis families and DEVELOPMENT experiments per cycle."""

    def __init__(self, budget: ResearchCycleBudget | None = None) -> None:
        self.budget = budget or ResearchCycleBudget()

    def check_experiment_quota(self) -> bool:
        """Check if remaining experiment quota permits another execution."""
        return self.budget.current_experiments_count < self.budget.max_development_experiments

    def consume_experiment_quota(self) -> None:
        """Record an experiment execution against the cycle budget."""
        if not self.check_experiment_quota():
            raise RuntimeError("RESEARCH CYCLE BUDGET EXCEEDED: Cannot execute more DEVELOPMENT experiments!")
        self.budget.current_experiments_count += 1
