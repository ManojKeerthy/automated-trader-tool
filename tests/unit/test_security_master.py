"""Unit tests for SecurityMaster and Security dataclass."""

from datetime import date

from tradecraft.universe.security_master import Security, SecurityMaster, SymbolHistoryRecord


def test_security_master_registration():
    master = SecurityMaster()
    sec = Security(
        security_uuid="sec-100",
        current_symbol="RELIANCE",
        name="Reliance Industries Ltd",
        isin="INE002A01018",
        listing_date=date(2000, 1, 1),
    )
    uuid_res = master.register_security(sec)
    assert uuid_res == "sec-100"

    assert master.get_by_uuid("sec-100") == sec
    assert master.get_by_symbol("RELIANCE") == sec
    assert master.get_by_isin("INE002A01018") == sec


def test_security_symbol_history_resolution():
    master = SecurityMaster()
    sec = Security(
        security_uuid="sec-200",
        current_symbol="MAHMRA",
        name="Mahindra & Mahindra Ltd",
        listing_date=date(1996, 1, 1),
        symbol_history=[
            SymbolHistoryRecord(
                effective_from=date(1996, 1, 1),
                effective_to=date(2020, 5, 1),
                old_symbol=None,
                new_symbol="M&M",
            ),
            SymbolHistoryRecord(
                effective_from=date(2020, 5, 2),
                effective_to=None,
                old_symbol="M&M",
                new_symbol="MAHMRA",
            ),
        ],
    )
    master.register_security(sec)

    assert sec.get_symbol_on(date(2015, 6, 1)) == "M&M"
    assert sec.get_symbol_on(date(2021, 1, 1)) == "MAHMRA"
