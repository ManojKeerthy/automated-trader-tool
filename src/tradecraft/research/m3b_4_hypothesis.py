"""Pre-registration framework and parameter selection provenance audit for M3B.4 V3 hypotheses."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

ALLOWED_PROVENANCE_CATEGORIES = {
    "INHERITED_FROM_V2",
    "STANDARD_TECHNICAL_CONVENTION",
    "ECONOMICALLY_DERIVED",
    "RISK_MODEL_DERIVED",
    "POST_HOC_DIAGNOSTIC_MOTIVATED",
}


@dataclass(frozen=True)
class V3ParameterOrigin:
    parameter_name: str
    v2_value: Any
    v3_value: Any
    provenance: str
    alternatives_tested: bool
    pnl_used_to_select: bool
    justification: str

    def audit(self) -> str:
        if self.provenance not in ALLOWED_PROVENANCE_CATEGORIES:
            return f"INVALID_PROVENANCE_CATEGORY: {self.provenance}"
        if self.alternatives_tested:
            return "OPTIMISED_ON_DEVELOPMENT: Alternative values were tested!"
        if self.pnl_used_to_select:
            return "OPTIMISED_ON_DEVELOPMENT: Historical P&L was inspected to select parameter!"
        return "PASS"


@dataclass(frozen=True)
class V3HypothesisPreRegistration:
    strategy_family: str
    parent_strategy_id: str
    parent_config_hash: str
    v3_strategy_id: str
    hypothesis_statement: str
    economic_rationale: str
    behavioural_rationale: str
    diagnosed_v2_failure: str
    post_hoc_evidence_used: str
    rule_changes: List[Dict[str, Any]]
    parameters: Dict[str, Any]
    parameter_origins: List[V3ParameterOrigin]
    expected_effect: str
    falsification_condition: str
    registered_at: str
    config_hash: str

    def audit_parameter_selection_provenance(self) -> None:
        """Run mandatory Parameter Selection Provenance Audit on all parameters."""
        for p in self.parameter_origins:
            result = p.audit()
            if result != "PASS":
                logger.error(f"PARAMETER PROVENANCE AUDIT FAILED for {p.parameter_name} in {self.v3_strategy_id}: {result}")
                raise RuntimeError(f"PARAMETER_SELECTION_PROVENANCE_FAILURE: {p.parameter_name} -> {result}")
        logger.info(f"PARAMETER PROVENANCE AUDIT PASSED for {self.v3_strategy_id}: All parameters verified without P&L optimization.")


class V3HypothesisRegistry:
    """Immutable registry for pre-registered V3 hypotheses."""

    def __init__(self, registry_file: Path = Path("scratch/m3b_4_v3_hypothesis_registry.json")):
        self.registry_file = registry_file
        self._registrations: Dict[str, V3HypothesisPreRegistration] = {}

    def register(self, reg: V3HypothesisPreRegistration) -> None:
        reg.audit_parameter_selection_provenance()
        if reg.v3_strategy_id in self._registrations:
            raise RuntimeError(f"IMMUTABILITY VIOLATION: Strategy {reg.v3_strategy_id} already registered!")
        self._registrations[reg.v3_strategy_id] = reg
        logger.info(f"PRE-REGISTERED V3 HYPOTHESIS: {reg.v3_strategy_id} (Config Hash: {reg.config_hash})")

    def export_json(self) -> None:
        out: Dict[str, Any] = {}
        for k, reg in self._registrations.items():
            out[k] = {
                "strategy_family": reg.strategy_family,
                "parent_strategy_id": reg.parent_strategy_id,
                "parent_config_hash": reg.parent_config_hash,
                "v3_strategy_id": reg.v3_strategy_id,
                "hypothesis_statement": reg.hypothesis_statement,
                "economic_rationale": reg.economic_rationale,
                "behavioural_rationale": reg.behavioural_rationale,
                "diagnosed_v2_failure": reg.diagnosed_v2_failure,
                "post_hoc_evidence_used": reg.post_hoc_evidence_used,
                "rule_changes": reg.rule_changes,
                "parameters": reg.parameters,
                "parameter_origins": [
                    {
                        "parameter_name": p.parameter_name,
                        "v2_value": p.v2_value,
                        "v3_value": p.v3_value,
                        "provenance": p.provenance,
                        "alternatives_tested": p.alternatives_tested,
                        "pnl_used_to_select": p.pnl_used_to_select,
                        "justification": p.justification,
                    }
                    for p in reg.parameter_origins
                ],
                "expected_effect": reg.expected_effect,
                "falsification_condition": reg.falsification_condition,
                "registered_at": reg.registered_at,
                "config_hash": reg.config_hash,
            }

        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(out, f, indent=2)
        logger.info(f"Exported frozen V3 hypothesis registry to {self.registry_file}")
