"""Benchmark Suite for standardized quantitative baseline comparisons."""

from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkDefinition:
    """Versioned benchmark definition."""
    benchmark_id: str
    name: str
    benchmark_type: str  # BUY_AND_HOLD, EQUAL_WEIGHT, RANDOM_ENTRY, COIN_FLIP, SMA200_TREND, PREVIOUS_BEST
    version: str = "1.0.0"
    description: str = ""


class BenchmarkSuite:
    """Automated benchmark comparison framework."""

    CANONICAL_BENCHMARKS = [
        ("BENCH-NIFTY50-BH", "Buy & Hold NIFTY 50 Index", "BUY_AND_HOLD"),
        ("BENCH-EQUAL-WEIGHT", "Buy & Hold Equal Weight Portfolio", "EQUAL_WEIGHT"),
        ("BENCH-RANDOM-ENTRY", "Random Entry Baseline", "RANDOM_ENTRY"),
        ("BENCH-COIN-FLIP", "Coin Flip Baseline", "COIN_FLIP"),
        ("BENCH-SMA200-TREND", "SMA200 Trend Filtered Baseline", "SMA200_TREND"),
        ("BENCH-PREV-BEST", "Previous Best Strategy Benchmark", "PREVIOUS_BEST"),
    ]

    def __init__(self) -> None:
        self._benchmarks: dict[str, BenchmarkDefinition] = {}
        self._initialize_canonical_benchmarks()

    def _initialize_canonical_benchmarks(self) -> None:
        for bid, name, btype in self.CANONICAL_BENCHMARKS:
            self._benchmarks[bid] = BenchmarkDefinition(
                benchmark_id=bid,
                name=name,
                benchmark_type=btype,
            )

    def get_benchmark(self, benchmark_id: str) -> BenchmarkDefinition | None:
        return self._benchmarks.get(benchmark_id)

    def list_benchmarks(self) -> list[BenchmarkDefinition]:
        return list(self._benchmarks.values())

    def compare_with_benchmarks(self, strategy_metrics: dict[str, float]) -> dict[str, Any]:
        """Compare strategy metrics against standard baseline benchmarks."""
        strat_return = strategy_metrics.get("net_return_pct", 0.0)
        strategy_metrics.get("sharpe_ratio", 0.0)

        # Baseline benchmark metric assumptions
        bench_returns = {
            "BENCH-NIFTY50-BH": 12.5,
            "BENCH-EQUAL-WEIGHT": 11.2,
            "BENCH-RANDOM-ENTRY": -2.1,
            "BENCH-COIN-FLIP": -1.8,
            "BENCH-SMA200-TREND": 8.4,
            "BENCH-PREV-BEST": 7.66,
        }

        comparisons = {}
        for bid, b_return in bench_returns.items():
            excess_return = strat_return - b_return
            comparisons[bid] = {
                "benchmark_return_pct": b_return,
                "strategy_return_pct": strat_return,
                "excess_return_pct": round(excess_return, 4),
                "outperformed": excess_return > 0,
            }
        return comparisons
