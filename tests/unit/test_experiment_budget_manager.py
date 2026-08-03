"""Unit tests for ExperimentBudgetManager."""

import pytest

from tradecraft.research.experiment_budget_manager import (
    ExperimentBudgetManager,
    ResearchCycleBudget,
)


def test_experiment_budget_manager():
    budget = ResearchCycleBudget(max_development_experiments=2)
    mgr = ExperimentBudgetManager(budget)

    assert mgr.check_experiment_quota() is True
    mgr.consume_experiment_quota()
    assert mgr.check_experiment_quota() is True
    mgr.consume_experiment_quota()

    assert mgr.check_experiment_quota() is False
    with pytest.raises(RuntimeError):
        mgr.consume_experiment_quota()
