from datetime import date
from decimal import Decimal

import pytest

from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.market_data.quality_engine import DataQualityEngine


@pytest.fixture
def quality_engine():
    cal = TradingCalendar()
    return DataQualityEngine(cal)


def test_validation_clean_data(quality_engine):
    bars = [
        {
            "trading_date": date(2026, 1, 27),
            "open": Decimal("100.00"),
            "high": Decimal("105.00"),
            "low": Decimal("98.00"),
            "close": Decimal("102.00"),
            "volume": 10000,
        },
        {
            "trading_date": date(2026, 1, 28),
            "open": Decimal("102.00"),
            "high": Decimal("103.00"),
            "low": Decimal("99.50"),
            "close": Decimal("101.00"),
            "volume": 12000,
        },
    ]
    alerts = quality_engine.validate_bars("TESTSTK", bars)
    # Filter out stale data warnings since today is later than Jan 2026
    non_stale_alerts = [a for a in alerts if a["category"] != "stale"]
    assert len(non_stale_alerts) == 0


def test_validation_invalid_ohlc(quality_engine):
    # High is less than Open
    bars = [
        {
            "trading_date": date(2026, 1, 27),
            "open": Decimal("100.00"),
            "high": Decimal("95.00"),
            "low": Decimal("90.00"),
            "close": Decimal("98.00"),
            "volume": 10000,
        },
    ]
    alerts = quality_engine.validate_bars("TESTSTK", bars)
    ohlc_alerts = [a for a in alerts if a["category"] == "ohlc_invalid"]
    assert len(ohlc_alerts) > 0
    assert ohlc_alerts[0]["level"] == "CRITICAL"


def test_validation_duplicates(quality_engine):
    # Duplicate dates
    bars = [
        {
            "trading_date": date(2026, 1, 27),
            "open": Decimal("100.00"),
            "high": Decimal("105.00"),
            "low": Decimal("98.00"),
            "close": Decimal("102.00"),
            "volume": 10000,
        },
        {
            "trading_date": date(2026, 1, 27),
            "open": Decimal("100.00"),
            "high": Decimal("105.00"),
            "low": Decimal("98.00"),
            "close": Decimal("102.00"),
            "volume": 10000,
        },
    ]
    alerts = quality_engine.validate_bars("TESTSTK", bars)
    dup_alerts = [a for a in alerts if a["category"] == "duplicate"]
    assert len(dup_alerts) > 0
    assert dup_alerts[0]["level"] == "ERROR"


def test_validation_negative_values(quality_engine):
    # Negative close
    bars = [
        {
            "trading_date": date(2026, 1, 27),
            "open": Decimal("100.00"),
            "high": Decimal("105.00"),
            "low": Decimal("98.00"),
            "close": Decimal("-10.00"),
            "volume": 10000,
        },
    ]
    alerts = quality_engine.validate_bars("TESTSTK", bars)
    neg_alerts = [a for a in alerts if a["category"] == "negative_values"]
    assert len(neg_alerts) > 0
    assert neg_alerts[0]["level"] == "CRITICAL"


def test_validation_suspicious_return(quality_engine):
    # Close changes from 100 to 130 (+30% single day return)
    bars = [
        {
            "trading_date": date(2026, 1, 27),
            "open": Decimal("100.00"),
            "high": Decimal("105.00"),
            "low": Decimal("98.00"),
            "close": Decimal("100.00"),
            "volume": 10000,
        },
        {
            "trading_date": date(2026, 1, 28),
            "open": Decimal("130.00"),
            "high": Decimal("135.00"),
            "low": Decimal("128.00"),
            "close": Decimal("130.00"),
            "volume": 12000,
        },
    ]
    alerts = quality_engine.validate_bars("TESTSTK", bars)
    ret_alerts = [a for a in alerts if a["category"] == "suspicious_return"]
    assert len(ret_alerts) > 0
    assert ret_alerts[0]["level"] == "WARNING"
