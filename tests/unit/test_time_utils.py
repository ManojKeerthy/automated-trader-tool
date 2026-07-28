from datetime import date, datetime

from tradecraft.core.time_utils import (
    MARKET_TZ,
    UTC_TZ,
    combine_date_time_market,
    now_in_market_tz,
    to_market_tz,
    to_utc,
)


def test_now_in_market_tz():
    now_market = now_in_market_tz()
    assert now_market.tzinfo == MARKET_TZ


def test_to_market_tz():
    # Naive datetime
    naive = datetime(2026, 7, 28, 12, 0, 0)
    market_dt = to_market_tz(naive)
    assert market_dt.tzinfo == MARKET_TZ
    # Converted correctly (naive assumed UTC in helper)
    assert market_dt.hour == 17  # 12:00 UTC + 5:30 = 17:30 IST
    assert market_dt.minute == 30

    # Timezone-aware UTC datetime
    aware_utc = datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC_TZ)
    market_dt2 = to_market_tz(aware_utc)
    assert market_dt2.tzinfo == MARKET_TZ
    assert market_dt2.hour == 17
    assert market_dt2.minute == 30


def test_to_utc():
    naive = datetime(2026, 7, 28, 12, 0, 0)  # Assumed Market TZ in helper
    utc_dt = to_utc(naive)
    assert utc_dt.tzinfo == UTC_TZ
    assert utc_dt.hour == 6  # 12:00 IST - 5:30 = 6:30 UTC
    assert utc_dt.minute == 30


def test_combine_date_time_market():
    d = date(2026, 7, 28)
    combined = combine_date_time_market(d, "09:15:00")
    assert combined.tzinfo == MARKET_TZ
    assert combined.year == 2026
    assert combined.month == 7
    assert combined.day == 28
    assert combined.hour == 9
    assert combined.minute == 15
    assert combined.second == 0
