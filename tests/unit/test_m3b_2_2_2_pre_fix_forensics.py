"""Pre-fix forensic unit tests for M3B.2.2.2 engine defects."""

import json
from decimal import Decimal
from pathlib import Path


def test_pre_fix_accounting_residuals_and_temporal_violations_captured():
    """Verify that pre-fix forensic evidence JSON exists and documents the exact accounting residuals."""
    evidence_path = Path("scratch/m3b_2_2_2_pre_fix_forensic_evidence.json")
    assert evidence_path.exists(), "Pre-fix forensic evidence JSON must exist!"

    with open(evidence_path) as f:
        data = json.load(f)

    # 1. Trend Pullback V2
    tp = data["Trend Pullback V2 Strategy"]
    assert tp["config_hash"] == "5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523"
    assert round(Decimal(tp["accounting_residual"]), 2) == Decimal("-6326.20")
    assert tp["total_temporal_violations"] == 113

    # 2. Breakout Confirmation V2
    bc = data["Breakout Confirmation V2 Strategy"]
    assert bc["config_hash"] == "f482e1baa26bdc15e7b589ff3baa06550a314f911db667062f553c029c4da213"
    assert round(Decimal(bc["accounting_residual"]), 2) == Decimal("-6769.28")
    assert bc["total_temporal_violations"] == 77

    # 3. Momentum Relative Strength V2
    mr = data["Momentum Relative Strength V2 Strategy"]
    assert mr["config_hash"] == "8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d"
    assert round(Decimal(mr["accounting_residual"]), 2) == Decimal("-3033.86")
    assert mr["total_temporal_violations"] == 56

    # 4. Mean Reversion V2
    mrev = data["Mean Reversion V2 Strategy"]
    assert mrev["config_hash"] == "8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82"
    assert round(Decimal(mrev["accounting_residual"]), 2) == Decimal("-3449.64")
    assert mrev["total_temporal_violations"] == 40
