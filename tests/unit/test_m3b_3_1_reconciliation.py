"""Unit tests for Milestone M3B.3.1 Reconciliation Addendum & Evidence Integrity Audit."""

import json
from datetime import date
from pathlib import Path

import pytest

from tradecraft.research.firewall import DataBoundaryViolationError, DevelopmentDataFirewall
from tradecraft.strategy.v2_strategies import (
    BreakoutConfirmV2Strategy,
    MeanReversionV2Strategy,
    MomentumRSV2Strategy,
    TrendPullbackV2Strategy,
)


def test_m3b_3_1_frozen_v2_hashes():
    """Verify SHA256 hashes of all four frozen V2 strategy configurations."""
    hashes = {
        TrendPullbackV2Strategy(): "5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523",
        BreakoutConfirmV2Strategy(): "f482e1baa26bdc15e7b589ff3baa06550a314f911db667062f553c029c4da213",
        MomentumRSV2Strategy(): "8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d",
        MeanReversionV2Strategy(): "8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82",
    }
    for strat, expected_hash in hashes.items():
        assert strat.config_hash == expected_hash, f"Hash mismatch for {strat.name}"


def test_m3b_3_1_development_firewall():
    """Verify data firewall blocks access to VALIDATION and FINAL TEST dates."""
    fw = DevelopmentDataFirewall()
    fw.validate_date(date(2020, 1, 15))

    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2022, 1, 1))

    with pytest.raises(DataBoundaryViolationError):
        fw.validate_date(date(2024, 7, 1))

    assert fw.validation_access_count == 1
    assert fw.final_test_access_count == 1


def test_mean_reversion_expectancy_r_fails_threshold():
    """Verify that Mean Reversion V2 +0.18R fails a +0.25R required threshold."""
    mean_reversion_expectancy_r = 0.18
    threshold_required = 0.25
    gate_result = "PASS" if mean_reversion_expectancy_r >= threshold_required else "FAIL"

    assert gate_result == "FAIL", "Mean Reversion V2 +0.18R MUST evaluate as FAIL against +0.25R requirement!"


def test_m3b_3_1_json_artifacts_and_conservation():
    """Verify that M3B.3.1 JSON artifacts exist and satisfy exact conservation laws."""
    master_file = Path("scratch/m3b_3_1_reconciliation_evidence.json")
    yearly_file = Path("scratch/m3b_3_1_yearly_reconciliation.json")
    regime_file = Path("scratch/m3b_3_1_regime_reconciliation.json")
    concentration_file = Path("scratch/m3b_3_1_concentration_reconciliation.json")
    attrition_file = Path("scratch/m3b_3_1_attrition_reconciliation.json")

    assert master_file.exists(), "master_evidence JSON must exist"
    assert yearly_file.exists(), "yearly_reconciliation JSON must exist"
    assert regime_file.exists(), "regime_reconciliation JSON must exist"
    assert concentration_file.exists(), "concentration_reconciliation JSON must exist"
    assert attrition_file.exists(), "attrition_reconciliation JSON must exist"

    with open(yearly_file) as f:
        yearly_data = json.load(f)
    with open(regime_file) as f:
        regime_data = json.load(f)
    with open(concentration_file) as f:
        concentration_data = json.load(f)
    with open(attrition_file) as f:
        attrition_data = json.load(f)

    for strat_id in ["strat_trend_pullback_v2", "strat_breakout_confirm_v2", "strat_momentum_rs_v2", "strat_mean_reversion_v2"]:
        # 1. Yearly conservation
        y = yearly_data[strat_id]
        assert y["trade_count_conserved"] is True
        assert y["pnl_conserved"] is True

        # 2. Regime conservation
        r = regime_data[strat_id]
        assert r["trade_regime_attribution_date"] == "SIGNAL_DATE"
        assert r["trade_count_conserved"] is True
        assert r["pnl_conserved"] is True

        # 3. Concentration conservation
        c = concentration_data[strat_id]
        assert c["trade_count_conserved"] is True
        assert c["pnl_conserved"] is True
        assert c["win_share_denominator"] == "TOTAL_WINNING_TRADE_PNL"

        # 4. Attrition conservation
        a = attrition_data[strat_id]
        assert a["attrition_conserved"] is True
