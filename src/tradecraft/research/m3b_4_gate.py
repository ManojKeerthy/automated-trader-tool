"""Authoritative Development Survivor Gate implementation for Milestone M3B.4."""

from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateCriterionResult:
    criterion_name: str
    observed_value: Any
    required_threshold: str
    operator: str
    gate_result: str  # PASS or FAIL
    provenance_quality: str


class DevelopmentSurvivorGateEvaluator:
    """Evaluates V3 strategies against frozen V2DevelopmentGate v1.0 criteria."""

    @staticmethod
    def evaluate(
        win_rate: float,
        profit_factor: float,
        expectancy_r: float,
        max_drawdown_pct: float,
        semester_concentration_pct: float,
    ) -> Dict[str, Any]:
        
        criteria = [
            GateCriterionResult(
                criterion_name="win_rate",
                observed_value=win_rate,
                required_threshold=">= 35.0%",
                operator=">=",
                gate_result="PASS" if win_rate >= 35.0 else "FAIL",
                provenance_quality="PREDECLARED_HEURISTIC",
            ),
            GateCriterionResult(
                criterion_name="profit_factor",
                observed_value=profit_factor,
                required_threshold=">= 1.30",
                operator=">=",
                gate_result="PASS" if profit_factor >= 1.30 else "FAIL",
                provenance_quality="PREDECLARED_AND_JUSTIFIED",
            ),
            GateCriterionResult(
                criterion_name="expectancy_r",
                observed_value=expectancy_r,
                required_threshold=">= +0.25 R",
                operator=">=",
                gate_result="PASS" if expectancy_r >= 0.25 else "FAIL",
                provenance_quality="PREDECLARED_AND_JUSTIFIED",
            ),
            GateCriterionResult(
                criterion_name="max_drawdown",
                observed_value=max_drawdown_pct,
                required_threshold="<= 25.0%",
                operator="<=",
                gate_result="PASS" if max_drawdown_pct <= 25.0 else "FAIL",
                provenance_quality="PREDECLARED_HEURISTIC",
            ),
            GateCriterionResult(
                criterion_name="semester_concentration",
                observed_value=semester_concentration_pct,
                required_threshold="<= 40.0%",
                operator="<=",
                gate_result="PASS" if semester_concentration_pct <= 40.0 else "FAIL",
                provenance_quality="PREDECLARED_AND_JUSTIFIED",
            ),
        ]

        overall_pass = all(c.gate_result == "PASS" for c in criteria)
        final_decision = "DEVELOPMENT_SURVIVOR" if overall_pass else "ABANDON_FAMILY"
        validation_status = "ELIGIBLE_FOR_FUTURE_VALIDATION" if overall_pass else "BLOCKED"

        return {
            "criteria_evaluations": {
                c.criterion_name: {
                    "observed_value": c.observed_value,
                    "required_threshold": c.required_threshold,
                    "operator": c.operator,
                    "gate_result": c.gate_result,
                    "provenance_quality": c.provenance_quality,
                }
                for c in criteria
            },
            "overall_gate_result": "PASS" if overall_pass else "FAIL",
            "final_decision": final_decision,
            "validation_status": validation_status,
        }
