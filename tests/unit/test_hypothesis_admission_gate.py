"""Unit tests for HypothesisAdmissionGate."""

from tradecraft.research.hypothesis_admission_gate import HypothesisAdmissionGate
from tradecraft.research.hypothesis_registry import HypothesisRecord


def test_hypothesis_admission_gate_evaluation():
    gate = HypothesisAdmissionGate()

    valid_hypo = HypothesisRecord(
        hypothesis_uuid="hypo-val-1",
        hypothesis_name="Valid Test Hypothesis",
        parent_hypothesis_uuid=None,
        economic_rationale="Solid economic rationale based on structural market flows.",
        behavioural_rationale="Over-reaction bias among momentum chasing investors.",
        expected_market_behaviour="Trend continuation.",
        falsification_criteria="Expectancy R < 0.25R",
        supporting_literature=["Test Literature Citation"],
    )
    res = gate.evaluate_hypothesis(valid_hypo)
    assert res.is_admitted is True
    assert len(res.failed_items) == 0

    invalid_hypo = HypothesisRecord(
        hypothesis_uuid="hypo-inval-1",
        hypothesis_name="Invalid Test Hypothesis",
        parent_hypothesis_uuid=None,
        economic_rationale="Short",
        behavioural_rationale="",
        expected_market_behaviour="None",
        falsification_criteria="",
        supporting_literature=[],
    )
    res_inval = gate.evaluate_hypothesis(invalid_hypo)
    assert res_inval.is_admitted is False
    assert len(res_inval.failed_items) > 0
