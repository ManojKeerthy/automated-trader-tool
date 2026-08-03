"""Experiment Comparison Engine for multi-run quantitative analytics."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ComparisonSummary:
    """Container for multi-experiment comparative metrics."""
    experiment_ids: list[str]
    metrics_matrix: dict[str, dict[str, float]]  # metric_name -> {exp_id: value}
    best_per_metric: dict[str, str]  # metric_name -> winning_exp_id


class ExperimentComparator:
    """Engine comparing experiments across 14 quantitative dimensions."""

    METRICS = [
        "cagr_pct", "max_drawdown_pct", "profit_factor", "expectancy_r",
        "sharpe_ratio", "sortino_ratio", "calmar_ratio", "turnover_pct",
        "exposure_pct", "trade_count", "win_rate_pct", "avg_holding_days",
        "semester_concentration_pct", "cost_sensitivity_bps"
    ]

    def compare_experiments(self, experiments_data: list[dict[str, Any]]) -> ComparisonSummary:
        """Compare multiple experiment metric dictionaries side by side."""
        exp_ids = [e["experiment_id"] for e in experiments_data]
        matrix: dict[str, dict[str, float]] = {m: {} for m in self.METRICS}
        best_per_metric: dict[str, str] = {}

        for e in experiments_data:
            exp_id = e["experiment_id"]
            metrics = e.get("metrics", {})
            for m in self.METRICS:
                val = float(metrics.get(m, 0.0))
                matrix[m][exp_id] = val

        for m in self.METRICS:
            # High is better for most, low is better for drawdown/turnover/concentration
            lower_is_better = m in {"max_drawdown_pct", "turnover_pct", "semester_concentration_pct", "cost_sensitivity_bps"}
            exp_vals = matrix[m]
            if exp_vals:
                best_exp = min(exp_vals, key=exp_vals.get) if lower_is_better else max(exp_vals, key=exp_vals.get)  # type: ignore[arg-type]
                best_per_metric[m] = best_exp

        return ComparisonSummary(
            experiment_ids=exp_ids,
            metrics_matrix=matrix,
            best_per_metric=best_per_metric,
        )
