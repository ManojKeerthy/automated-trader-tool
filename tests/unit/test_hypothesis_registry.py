"""Unit tests for HypothesisRegistry."""

import pytest
from tradecraft.research.hypothesis_registry import HypothesisRecord, HypothesisRegistry


def test_hypothesis_registration_and_status_update():
    reg = HypothesisRegistry()
    record = HypothesisRecord(
        hypothesis_uuid="hypo-1",
        hypothesis_name="Test Hypothesis",
        parent_hypothesis_uuid=None,
        economic_rationale="Market overreaction",
        behavioural_rationale="Herd behavior",
        expected_market_behaviour="Reversal",
        falsification_criteria="PF < 1.30",
        supporting_literature=["Test Paper"],
    )
    reg.register_hypothesis(record)
    assert len(record.checksum) == 64
    assert reg.get_hypothesis("hypo-1") == record

    reg.update_status("hypo-1", "FAILED")
    assert reg.get_hypothesis("hypo-1").status == "FAILED"
