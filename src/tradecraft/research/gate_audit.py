"""Historical Gate Provenance Audit for V2DevelopmentGate v1.0."""

from dataclasses import dataclass
from enum import Enum


class GateProvenanceClassification(str, Enum):
    PREDECLARED_AND_JUSTIFIED = "PREDECLARED_AND_JUSTIFIED"
    PREDECLARED_HEURISTIC = "PREDECLARED_HEURISTIC"
    POST_HOC_ORIGIN_UNCLEAR = "POST_HOC_ORIGIN_UNCLEAR"


@dataclass(frozen=True)
class GateCriterionAudit:
    metric_name: str
    threshold_value: str
    original_rationale: str
    source_provenance: str
    predeclared_before_v2_results: bool
    economic_or_statistical_justification: str
    classification: GateProvenanceClassification


class GateProvenanceAuditor:
    """Audits the provenance and justification of V2DevelopmentGate v1.0 criteria."""

    @classmethod
    def audit_all(cls) -> list[GateCriterionAudit]:
        return [
            GateCriterionAudit(
                metric_name="win_rate",
                threshold_value=">= 35.0%",
                original_rationale="Ensure signal quality provides sufficient winning trades for swing strategies.",
                source_provenance="M3B.2 SignalViabilityPolicy v1.0 specification (Pre-v2 execution)",
                predeclared_before_v2_results=True,
                economic_or_statistical_justification="Heuristic filter intended to prevent excessive trade friction from low-win-rate systems; however, high-payoff strategies can mathematically achieve positive expectancy below 35%.",
                classification=GateProvenanceClassification.PREDECLARED_HEURISTIC,
            ),
            GateCriterionAudit(
                metric_name="profit_factor",
                threshold_value=">= 1.30",
                original_rationale="Ensure gross profits exceed gross losses by at least 30% after friction.",
                source_provenance="M2 Backtesting & Strategy Foundation specification",
                predeclared_before_v2_results=True,
                economic_or_statistical_justification="Statistically justified buffer ensuring net edge survives live execution slippage and model degradation.",
                classification=GateProvenanceClassification.PREDECLARED_AND_JUSTIFIED,
            ),
            GateCriterionAudit(
                metric_name="expectancy_r",
                threshold_value=">= 0.25 R",
                original_rationale="Minimum positive expectancy per unit of risk required to achieve capital growth.",
                source_provenance="M3B Research Strategy Laboratory specification",
                predeclared_before_v2_results=True,
                economic_or_statistical_justification="Economically justified threshold covering round-trip friction and fixed costs in Indian equity delivery markets.",
                classification=GateProvenanceClassification.PREDECLARED_AND_JUSTIFIED,
            ),
            GateCriterionAudit(
                metric_name="semester_concentration",
                threshold_value="<= 40.0%",
                original_rationale="Ensure confirmed signals are distributed across market episodes rather than isolated to one 6-month period.",
                source_provenance="M3B.2 Clarification Amendment 1 (User Directive)",
                predeclared_before_v2_results=True,
                economic_or_statistical_justification="Mathematically sound rolling semester window filter ensuring temporal stability.",
                classification=GateProvenanceClassification.PREDECLARED_AND_JUSTIFIED,
            ),
            GateCriterionAudit(
                metric_name="max_drawdown",
                threshold_value="<= 25.0%",
                original_rationale="Capital preservation boundary preventing catastrophic equity decline.",
                source_provenance="M2 Portfolio & Risk Management specification",
                predeclared_before_v2_results=True,
                economic_or_statistical_justification="Standard risk management constraint for swing trading systems.",
                classification=GateProvenanceClassification.PREDECLARED_HEURISTIC,
            ),
        ]
