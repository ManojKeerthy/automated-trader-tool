from datetime import date

from tradecraft.market_data.calendar import TradingCalendar


def test_calendar_trading_day():
    cal = TradingCalendar()

    # 2026-01-26 is Republic Day (holiday)
    assert not cal.is_trading_day(date(2026, 1, 26))

    # 2026-01-27 is a normal Tuesday (trading day)
    assert cal.is_trading_day(date(2026, 1, 27))

    # Weekends (e.g. 2026-01-24 and 2026-01-25) are not trading days
    assert not cal.is_trading_day(date(2026, 1, 24))
    assert not cal.is_trading_day(date(2026, 1, 25))


def test_calendar_muhurat_trading():
    cal = TradingCalendar()
    # 2026-11-08 is Diwali Laxmi Pujan (Sunday, Muhurat Trading)
    assert cal.is_trading_day(date(2026, 11, 8))


def test_calendar_navigation():
    cal = TradingCalendar()
    # Republic day: Monday 2026-01-26
    # Previous trading day should be Friday 2026-01-23
    assert cal.previous_trading_day(date(2026, 1, 26)) == date(2026, 1, 23)

    # Next trading day should be Tuesday 2026-01-27
    assert cal.next_trading_day(date(2026, 1, 26)) == date(2026, 1, 27)


def test_calendar_sessions_between():
    cal = TradingCalendar()
    # Range covering Republic Day 2026-01-26
    start = date(2026, 1, 23)  # Friday
    end = date(2026, 1, 27)  # Tuesday

    sessions = cal.sessions_between(start, end)
    # Expected sessions: Friday (23rd), Tuesday (27th)
    # Sat (24th), Sun (25th), and Mon (26th, Holiday) are excluded
    assert sessions == [date(2026, 1, 23), date(2026, 1, 27)]


def test_calendar_validation_run():
    cal = TradingCalendar()
    # 2026 validation check should pass
    assert cal.run_calendar_validation(year=2026) is True


def test_calendar_overrides():
    from tradecraft.market_data.nse_calendar import NSETradingCalendar

    # Load calendar without data-dir file overrides for clean test
    cal = NSETradingCalendar(use_overrides=False)

    test_date = date(2026, 6, 1)  # A Monday, normally a trading day
    assert cal.is_trading_day(test_date) is True

    # Override it as a holiday
    cal.add_holiday_override(test_date)
    assert cal.is_trading_day(test_date) is False

    # Overriding weekend as a special session
    weekend_date = date(2026, 6, 6)  # A Saturday
    assert cal.is_trading_day(weekend_date) is False
    cal.add_special_session_override(weekend_date)
    assert cal.is_trading_day(weekend_date) is True


def test_calendar_verification_failure():
    import pytest

    from tradecraft.core.exceptions import CalendarError
    from tradecraft.market_data.nse_calendar import NSETradingCalendar

    cal = NSETradingCalendar(use_overrides=False)

    # If we claim a trading day is expected to be a holiday:
    with pytest.raises(CalendarError) as exc_info:
        cal.verify_against_manifest(
            expected_holidays={date(2026, 1, 27)},  # A trading day
            expected_sessions=set(),
        )
    assert "Disagreement" in str(exc_info.value)
