"""Unit tests for UniverseAPI."""

from datetime import date

from tradecraft.universe.historical_membership import HistoricalMembershipEngine, MembershipRecord
from tradecraft.universe.security_master import Security, SecurityMaster
from tradecraft.universe.universe_api import UniverseAPI
from tradecraft.universe.universe_registry import UniverseRegistry


def test_universe_api_get_constituents():
    master = SecurityMaster()
    reg = UniverseRegistry()
    membership = HistoricalMembershipEngine()

    sec1 = Security(
        security_uuid="s1",
        current_symbol="TCS",
        name="Tata Consultancy Services",
        listing_date=date(2004, 1, 1),
    )
    sec2 = Security(
        security_uuid="s2", current_symbol="INFY", name="Infosys Ltd", listing_date=date(1995, 1, 1)
    )
    master.register_security(sec1)
    master.register_security(sec2)

    membership.add_membership_record(
        MembershipRecord(security_uuid="s1", universe_id="NIFTY50", effective_from=date(2016, 1, 1))
    )
    membership.add_membership_record(
        MembershipRecord(security_uuid="s2", universe_id="NIFTY50", effective_from=date(2016, 1, 1))
    )

    api = UniverseAPI(master, reg, membership)
    constituents = api.get_constituents("NIFTY50", date(2018, 5, 1))
    uuids = [s.security_uuid for s in constituents]

    assert "s1" in uuids
    assert "s2" in uuids
    assert len(constituents) == 2
