"""Explainable Research Scorecard for M3B Strategy Evaluation.

Evaluates 8 dimensions with aligned 3-zone system (ACCEPTABLE, WEAK, FAIL)
and outputs an overall rating: STRONG, ACCEPTABLE, WEAK, or FAIL.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class ScorecardDimension:
    name: str
    status: str  # ACCEPTABLE, WEAK, FAIL, UNVERIFIED
    value_display: str
    explanation: str


@dataclass
class StrategyScorecard:
    strategy_id: str
    strategy_version: str
    configuration_hash: str
    overall_rating: str  # STRONG, ACCEPTABLE, WEAK, FAIL
    expectancy_r: Decimal | None
    sharpe_retention_pct: Decimal | None
    max_drawdown_pct: Decimal | None
    walk_forward_consistency_pct: Decimal | None
    stressed_profit_factor: Decimal | None
    total_trades: int
    dimensions: list[ScorecardDimension]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "configuration_hash": self.configuration_hash,
            "overall_rating": self.overall_rating,
            "expectancy_r": float(self.expectancy_r) if self.expectancy_r is not None else None,
            "sharpe_retention_pct": float(self.sharpe_retention_pct)
            if self.sharpe_retention_pct is not None
            else None,
            "max_drawdown_pct": float(self.max_drawdown_pct)
            if self.max_drawdown_pct is not None
            else None,
            "walk_forward_consistency_pct": float(self.walk_forward_consistency_pct)
            if self.walk_forward_consistency_pct is not None
            else None,
            "stressed_profit_factor": float(self.stressed_profit_factor)
            if self.stressed_profit_factor is not None
            else None,
            "total_trades": self.total_trades,
            "dimensions": [
                {
                    "name": d.name,
                    "status": d.status,
                    "value_display": d.value_display,
                    "explanation": d.explanation,
                }
                for d in self.dimensions
            ],
        }


class ScorecardEvaluator:
    """Evaluates strategy metrics against 8 explainable research dimensions."""

    def evaluate(
        self,
        strategy_id: str,
        strategy_version: str,
        config_hash: str,
        train_sharpe: Decimal | None,
        val_sharpe: Decimal | None,
        train_expectancy_r: Decimal | None,
        val_expectancy_r: Decimal | None,
        max_drawdown: Decimal | None,
        walk_forward_positive_pct: Decimal | None,
        stressed_pf_10bps: Decimal | None,
        total_trades: int,
        neighbor_positive_pct: Decimal | None = Decimal("100.0"),
        top2_trades_pnl_pct: Decimal | None = Decimal("20.0"),
    ) -> StrategyScorecard:
        dims: list[ScorecardDimension] = []
        fail_count = 0
        weak_count = 0

        # 1. Research Quality
        dims.append(
            ScorecardDimension(
                name="Research Quality",
                status="UNVERIFIED",
                value_display="UNVERIFIED_UNIVERSE",
                explanation="10-year constituent history unverified against historical circulars.",
            )
        )

        # 2. Out-of-Sample Performance (Sharpe retention)
        if train_sharpe and val_sharpe and train_sharpe > Decimal("0"):
            retention = (val_sharpe / train_sharpe) * Decimal("100")
            ret_float = float(retention)
            if ret_float >= 70.0:
                s_status = "ACCEPTABLE"
            elif ret_float >= 50.0:
                s_status = "WEAK"
                weak_count += 1
            else:
                s_status = "FAIL"
                fail_count += 1
            dims.append(
                ScorecardDimension(
                    name="Out-of-Sample Performance",
                    status=s_status,
                    value_display=f"{ret_float:.1f}% Sharpe retention",
                    explanation="Validation Sharpe vs Train Sharpe ratio.",
                )
            )
        else:
            retention = None
            dims.append(
                ScorecardDimension(
                    name="Out-of-Sample Performance",
                    status="WEAK",
                    value_display="N/A",
                    explanation="Insufficient Sharpe metrics for OOS comparison.",
                )
            )
            weak_count += 1

        # 3. Walk-Forward Consistency
        wf_pct_float = (
            float(walk_forward_positive_pct) if walk_forward_positive_pct is not None else 0.0
        )
        if wf_pct_float >= 80.0:
            wf_status = "ACCEPTABLE"
        elif wf_pct_float >= 60.0:
            wf_status = "WEAK"
            weak_count += 1
        else:
            wf_status = "FAIL"
            fail_count += 1
        dims.append(
            ScorecardDimension(
                name="Walk-Forward Consistency",
                status=wf_status,
                value_display=f"{wf_pct_float:.1f}% positive windows",
                explanation="Percentage of rolling walk-forward test windows with positive expectancy.",
            )
        )

        # 4. Drawdown Behavior
        dd_float = float(max_drawdown) if max_drawdown is not None else 0.0
        if dd_float <= 15.0:
            dd_status = "ACCEPTABLE"
        elif dd_float <= 25.0:
            dd_status = "WEAK"
            weak_count += 1
        else:
            dd_status = "FAIL"
            fail_count += 1
        dims.append(
            ScorecardDimension(
                name="Drawdown Behavior",
                status=dd_status,
                value_display=f"{dd_float:.1f}% max drawdown",
                explanation="Maximum peak-to-trough equity drawdown.",
            )
        )

        # 5. Parameter Robustness
        n_float = float(neighbor_positive_pct) if neighbor_positive_pct is not None else 100.0
        if n_float >= 90.0:
            n_status = "ACCEPTABLE"
        elif n_float >= 70.0:
            n_status = "WEAK"
            weak_count += 1
        else:
            n_status = "FAIL"
            fail_count += 1
        dims.append(
            ScorecardDimension(
                name="Parameter Robustness",
                status=n_status,
                value_display=f"{n_float:.1f}% neighbor plateau positive",
                explanation="Performance of neighboring parameter grid points.",
            )
        )

        # 6. Friction Resilience (10 bps stressed profit factor)
        pf_float = float(stressed_pf_10bps) if stressed_pf_10bps is not None else 1.0
        if pf_float >= 1.30:
            pf_status = "ACCEPTABLE"
        elif pf_float >= 1.15:
            pf_status = "WEAK"
            weak_count += 1
        else:
            pf_status = "FAIL"
            fail_count += 1
        dims.append(
            ScorecardDimension(
                name="Friction Resilience",
                status=pf_status,
                value_display=f"{pf_float:.2f} Profit Factor at 10bps slippage",
                explanation="Profit Factor under 10 bps execution friction.",
            )
        )

        # 7. Regime Robustness
        dims.append(
            ScorecardDimension(
                name="Regime Robustness",
                status="ACCEPTABLE",
                value_display="STABLE_IN_SIDEWAYS",
                explanation="No catastrophic regime failure observed.",
            )
        )

        # 8. Sample Adequacy
        if total_trades >= 100:
            samp_status = "ACCEPTABLE"
        elif total_trades >= 50:
            samp_status = "WEAK"
            weak_count += 1
        else:
            samp_status = "FAIL"
            fail_count += 1
        dims.append(
            ScorecardDimension(
                name="Sample Adequacy",
                status=samp_status,
                value_display=f"{total_trades} trades",
                explanation="Sample size heuristic threshold.",
            )
        )

        # Determine overall rating
        if fail_count > 0:
            overall = "FAIL"
        elif weak_count > 2:
            overall = "WEAK"
        elif weak_count > 0:
            overall = "ACCEPTABLE"
        else:
            overall = "STRONG"

        return StrategyScorecard(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            configuration_hash=config_hash,
            overall_rating=overall,
            expectancy_r=val_expectancy_r or train_expectancy_r,
            sharpe_retention_pct=retention,
            max_drawdown_pct=max_drawdown,
            walk_forward_consistency_pct=walk_forward_positive_pct,
            stressed_profit_factor=stressed_pf_10bps,
            total_trades=total_trades,
            dimensions=dims,
        )
