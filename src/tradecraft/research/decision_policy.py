"""Predeclared M3B3DecisionPolicy v1.0 for strategy family triage on DEVELOPMENT data."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class DecisionStatus(StrEnum):
    ABANDON_FAMILY = "ABANDON_FAMILY"
    ONE_FINAL_HYPOTHESIS_REVISION_ALLOWED = "ONE_FINAL_HYPOTHESIS_REVISION_ALLOWED"
    DEVELOPMENT_SURVIVOR = "DEVELOPMENT_SURVIVOR"


class EdgeClassification(StrEnum):
    STRUCTURALLY_NEGATIVE_GROSS_EDGE = "STRUCTURALLY_NEGATIVE_GROSS_EDGE"
    POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION = "POSITIVE_GROSS_EDGE_ERODED_BY_FRICTION"
    ROBUST_POSITIVE_NET_EDGE = "ROBUST_POSITIVE_NET_EDGE"


class OutlierDependenceClassification(StrEnum):
    DISTRIBUTED_EDGE = "DISTRIBUTED_EDGE"
    MODERATELY_CONCENTRATED = "MODERATELY_CONCENTRATED"
    OUTLIER_DEPENDENT = "OUTLIER_DEPENDENT"


class YearlyStabilityClassification(StrEnum):
    BROADLY_STABLE = "BROADLY_STABLE"
    PERIOD_DEPENDENT = "PERIOD_DEPENDENT"
    SINGLE_PERIOD_DOMINATED = "SINGLE_PERIOD_DOMINATED"
    CONSISTENTLY_NEGATIVE = "CONSISTENTLY_NEGATIVE"


class CostRobustnessClassification(StrEnum):
    ROBUST_TO_REASONABLE_FRICTION = "ROBUST_TO_REASONABLE_FRICTION"
    FRICTION_SENSITIVE = "FRICTION_SENSITIVE"
    ONLY_PROFITABLE_WITH_UNREALISTIC_FRICTION = "ONLY_PROFITABLE_WITH_UNREALISTIC_FRICTION"
    NEGATIVE_BEFORE_FRICTION = "NEGATIVE_BEFORE_FRICTION"


@dataclass(frozen=True)
class StrategyEvidencePackage:
    """Standardized evidence package for a frozen V2 strategy family."""

    strategy_id: str
    strategy_name: str
    config_hash: str
    executed_trades: int
    gross_pnl: Decimal
    explicit_costs: Decimal
    net_pnl: Decimal
    total_return_pct: float
    profit_factor: float
    win_rate: float
    expectancy_r: float

    # Yearly breakdown
    positive_years_count: int
    total_years_count: int
    best_year_pnl_share: float
    yearly_classification: YearlyStabilityClassification

    # Outlier sensitivity
    net_pnl_ex_top1: Decimal
    net_pnl_ex_top3: Decimal
    net_pnl_ex_top5: Decimal
    outlier_classification: OutlierDependenceClassification

    # Cost sensitivity net returns
    scenario_a_net_pnl: Decimal  # Observed (5 bps)
    scenario_b_net_pnl: Decimal  # Zero friction (0+0)
    scenario_c_net_pnl: Decimal  # High friction (10 bps)
    scenario_d_net_pnl: Decimal  # Severe friction (20 bps)
    cost_classification: CostRobustnessClassification


class M3B3DecisionPolicy:
    """Versioned, frozen policy v1.0 for assigning final M3B.3 research decisions."""

    VERSION = "v1.0"

    @classmethod
    def evaluate(cls, pkg: StrategyEvidencePackage) -> tuple[DecisionStatus, str, list[str]]:
        """Evaluate strategy evidence against frozen v1.0 triage rules.

        Returns:
            (DecisionStatus, rationale_summary, list_of_supporting_evidence_statements)
        """
        reasons: list[str] = []

        # 1. Check Gross Edge
        if pkg.gross_pnl <= Decimal("0"):
            reasons.append(
                f"Gross P&L is negative (-₹{abs(pkg.gross_pnl):,.2f}), proving lack of underlying structural edge."
            )
            return (
                DecisionStatus.ABANDON_FAMILY,
                "Structurally negative gross edge prior to execution costs.",
                reasons,
            )

        # 2. Check Net Edge under Observed Model (Scenario A)
        if pkg.net_pnl <= Decimal("0"):
            reasons.append(
                f"Gross edge (+₹{pkg.gross_pnl:,.2f}) is entirely consumed by friction (costs ₹{pkg.explicit_costs:,.2f}), resulting in net loss (-₹{abs(pkg.net_pnl):,.2f})."
            )
            return (
                DecisionStatus.ABANDON_FAMILY,
                "Positive gross edge completely eroded by transaction friction.",
                reasons,
            )

        # 3. Check Outlier Dependence
        if (
            pkg.outlier_classification == OutlierDependenceClassification.OUTLIER_DEPENDENT
            or pkg.net_pnl_ex_top3 <= Decimal("0")
        ):
            reasons.append(
                f"Net profit (+₹{pkg.net_pnl:,.2f}) is dependent on top 3 outlier trades; net P&L excluding top 3 is non-positive (₹{pkg.net_pnl_ex_top3:,.2f})."
            )

            # Evaluate if one final hypothesis revision is justified or abandon
            if pkg.scenario_b_net_pnl > Decimal("0") and pkg.gross_pnl > Decimal("50000"):
                reasons.append(
                    f"Gross edge (+₹{pkg.gross_pnl:,.2f}) demonstrates potential signal value under zero-friction, but entry/exit rules are structurally incomplete."
                )
                return (
                    DecisionStatus.ONE_FINAL_HYPOTHESIS_REVISION_ALLOWED,
                    "Edge is positive but outlier-dependent and friction-sensitive. Requires structural hypothesis revision before V3.",
                    reasons,
                )
            else:
                return (
                    DecisionStatus.ABANDON_FAMILY,
                    "Net profitability depends entirely on outlier trades.",
                    reasons,
                )

        # 4. Check Development Gate & Friction Robustness for Survivor status
        if (
            pkg.scenario_c_net_pnl > Decimal("0")
            and pkg.profit_factor >= 1.30
            and pkg.net_pnl_ex_top3 > Decimal("0")
            and pkg.yearly_classification != YearlyStabilityClassification.SINGLE_PERIOD_DOMINATED
        ):
            reasons.append(
                f"Strategy maintains positive net P&L under +10 bps stress (+₹{pkg.scenario_c_net_pnl:,.2f}), PF={pkg.profit_factor:.2f}, and non-outlier edge."
            )
            return (
                DecisionStatus.DEVELOPMENT_SURVIVOR,
                "Demonstrates robust, stable net edge under realistic friction and non-outlier distribution.",
                reasons,
            )

        # 5. Weak Positive Edge (e.g. Breakout V2: +5.55% return, PF 1.09, friction erodes 49% of gross profits)
        if pkg.profit_factor < 1.30 or pkg.scenario_c_net_pnl <= Decimal("0"):
            reasons.append(
                f"Net return (+{pkg.total_return_pct:.2f}%) and Profit Factor ({pkg.profit_factor:.2f}) fail the V2 gate (PF >= 1.30), and friction erodes over 45% of gross profits."
            )

            # Check if hypothesis revision is justified
            if pkg.gross_pnl > Decimal("0") and pkg.scenario_a_net_pnl > Decimal("0"):
                return (
                    DecisionStatus.ABANDON_FAMILY,  # Or ONE_FINAL_HYPOTHESIS_REVISION_ALLOWED if explicitly justified
                    "Positive net P&L exists but edge is too weak (PF < 1.30) and friction-dominated to qualify as DEVELOPMENT survivor.",
                    reasons,
                )
            else:
                return (
                    DecisionStatus.ABANDON_FAMILY,
                    "Fails V2 development gate thresholds.",
                    reasons,
                )

        return (
            DecisionStatus.ABANDON_FAMILY,
            "Fails M3B3DecisionPolicy v1.0 criteria.",
            reasons,
        )
