"""Unit tests for HistoricalMembershipEngine."""

from datetime import date
import pytest
from tradecraft.universe.historical_membership import HistoricalMembershipEngine, MembershipRecord


def test_historical_membership_point_in_time_query():
    engine = HistoricalMembershipEngine()
    engine.add_membership_record(
        MembershipRecord(
            security_uuid="sec-1",
            universe_id="NIFTY50",
            effective_from=date(2015, 1, 1),
            effective_to=date(2020, 12, 31),
        )
    )
    engine.add_membership_record(
        MembershipRecord(
            security_uuid="sec-2",
            universe_id="NIFTY50",
            effective_from=date(2018, 1, 1),
            effective_to=None,
        )
    )

    # Date in 2016: only sec-1 is member
    assert engine.get_constituents(date(2016, 6, 1), "NIFTY50") == ["sec-1"]

    # Date in 2019: both sec-1 and sec-2 are members
    assert engine.get_constituents(date(2019, 6, 1), "NIFTY50") == ["sec-1", "sec-2"]

    # Date in 2021: only sec-2 is member
    assert engine.get_constituents(date(2021, 6, 1), "NIFTY50") == ["sec-2"]
