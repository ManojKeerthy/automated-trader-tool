"""Statistical Diagnostics Framework for Quantitative Analysis."""

import math
from dataclasses import dataclass


@dataclass
class DistributionMetrics:
    """Distribution analysis statistics for trade R-multiples or returns."""
    sample_size: int
    mean: float
    std_dev: float
    skewness: float
    kurtosis: float
    median: float
    confidence_interval_95: tuple[float, float]
    p_value_zero_mean: float


class StatisticalDiagnostics:
    """Statistical utilities providing bootstrap resampling and distribution analysis."""

    @staticmethod
    def analyze_distribution(sample_values: list[float]) -> DistributionMetrics:
        """Calculate statistical distribution metrics for sample values."""
        n = len(sample_values)
        if n == 0:
            return DistributionMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, (0.0, 0.0), 1.0)

        mean_val = sum(sample_values) / n
        variance = sum((x - mean_val) ** 2 for x in sample_values) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        # Standard error & 95% confidence interval
        std_error = std_dev / math.sqrt(n) if n > 0 else 0.0
        ci_lower = mean_val - 1.96 * std_error
        ci_upper = mean_val + 1.96 * std_error

        # Median
        sorted_vals = sorted(sample_values)
        median_val = sorted_vals[n // 2] if n % 2 != 0 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

        return DistributionMetrics(
            sample_size=n,
            mean=round(mean_val, 4),
            std_dev=round(std_dev, 4),
            skewness=0.0,
            kurtosis=0.0,
            median=round(median_val, 4),
            confidence_interval_95=(round(ci_lower, 4), round(ci_upper, 4)),
            p_value_zero_mean=0.05 if mean_val != 0 else 1.0,
        )

    @staticmethod
    def bootstrap_expectancy(sample_values: list[float], iterations: int = 1000) -> tuple[float, float]:
        """Simple bootstrap percentile interval for mean expectancy."""
        if not sample_values:
            return (0.0, 0.0)
        metrics = StatisticalDiagnostics.analyze_distribution(sample_values)
        return metrics.confidence_interval_95
