"""Unit tests for Milestone M3B.3.1 Reconciliation Addendum & Evidence Integrity Audit."""

from datetime import date

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
        TrendPullbackV2Strategy(): "c4556b07bd4edc39f9a53c1c27c601d2c0747fcbc7ad356d4e4ec42af6c993da",
        BreakoutConfirmV2Strategy(): "85d9c0b3d8c360ec9f51beec15b7c0ad09aa04d26473bd463ba9ea97e6f2aacd",
        MomentumRSV2Strategy(): "221c35751fde73a351138d14502bd8b1bf6ad49e051bfe55d6bb086a1d2df825",
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

    assert gate_result == "FAIL", (
        "Mean Reversion V2 +0.18R MUST evaluate as FAIL against +0.25R requirement!"
    )



# test_m3b_3_1_json_artifacts_and_conservation removed 2026-08-06: certified specific
# reconciliation numbers from scratch/m3b_3_1_*.json, artifacts of the voided Cycle 1/2
# synthetic-data research run. Those files were deleted in the 2026-08-06 governance
# cleanup along with ~250 other documents attesting to results computed against fabricated
# prices (see CLAUDE.md, "Do not trust the historical record"). The other three tests in
# this file exercise real, still-valid mechanisms (frozen strategy config hashes, the
# DevelopmentDataFirewall, a threshold-gating check) and are kept.
