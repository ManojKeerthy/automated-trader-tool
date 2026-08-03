"""Unit tests for SurvivorshipGuard."""

from datetime import date
import pytest
from tradecraft.universe.security_master import Security, SecurityMaster
from tradecraft.universe.survivorship_guard import SurvivorshipGuard, SurvivorshipBiasError


def test_survivorship_guard_boundary_checks():
    master = SecurityMaster()
    sec = Security(
        security_uuid="sec-ipo-test",
        current_symbol="ZOMATO",
        name="Zomato Ltd",
        listing_date=date(2021, 7, 23),
        delisting_date=date(2025, 12, 31),
    )
    master.register_security(sec)
    guard = SurvivorshipGuard(master)

    # Valid date query
    guard.validate_security_access("sec-ipo-test", date(2022, 1, 1))

    # Pre-IPO query should raise error
    with pytest.raises(SurvivorshipBiasError):
        guard.validate_security_access("sec-ipo-test", date(2020, 1, 1))

    # Post-delisting query should raise error
    with pytest.raises(SurvivorshipBiasError):
        guard.validate_security_access("sec-ipo-test", date(2026, 1, 1))
