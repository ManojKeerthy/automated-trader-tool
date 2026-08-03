"""Unit tests for StatisticalDiagnostics."""

import pytest
from tradecraft.research.statistical_diagnostics import StatisticalDiagnostics


def test_statistical_diagnostics_analysis():
    metrics = StatisticalDiagnostics.analyze_distribution([1.0, 2.0, 3.0, 4.0, 5.0])
    assert metrics.sample_size == 5
    assert metrics.mean == 3.0
    assert metrics.median == 3.0
    assert metrics.confidence_interval_95[0] < 3.0 < metrics.confidence_interval_95[1]
