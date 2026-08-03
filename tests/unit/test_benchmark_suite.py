"""Unit tests for BenchmarkSuite."""

import pytest
from tradecraft.research.benchmark_suite import BenchmarkSuite


def test_benchmark_suite_comparison():
    suite = BenchmarkSuite()
    assert len(suite.list_benchmarks()) == 6
    comp = suite.compare_with_benchmarks({"net_return_pct": 15.0, "sharpe_ratio": 1.2})
    assert "BENCH-NIFTY50-BH" in comp
    assert comp["BENCH-NIFTY50-BH"]["outperformed"] is True
