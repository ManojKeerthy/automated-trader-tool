import logging
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.market_data.calendar import TradingCalendar

logger = logging.getLogger(__name__)


class DataQualityEngine:
    """Validates daily market OHLCV bars for correctness and completeness."""

    def __init__(self, calendar: TradingCalendar):
        self.calendar = calendar

    def validate_bars(self, symbol: str, bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate list of daily bars for a given symbol.

        Returns a list of alerts. Each alert is a dict with keys:
            - 'level': INFO, WARNING, ERROR, CRITICAL
            - 'category': duplicate, missing_session, ohlc_invalid, negative_values, suspicious_return, stale
            - 'message': description
            - 'trading_date': date or None
        """
        alerts: list[dict[str, Any]] = []
        if not bars:
            alerts.append(
                {
                    "level": "CRITICAL",
                    "category": "stale",
                    "message": f"No data found for symbol {symbol}",
                    "trading_date": None,
                }
            )
            return alerts

        # Sort bars by date
        sorted_bars = sorted(bars, key=lambda x: x["trading_date"])
        dates_present = {b["trading_date"] for b in sorted_bars}

        # Check duplicates
        if len(dates_present) < len(sorted_bars):
            seen_dates = set()
            for b in sorted_bars:
                d = b["trading_date"]
                if d in seen_dates:
                    alerts.append(
                        {
                            "level": "ERROR",
                            "category": "duplicate",
                            "message": f"Duplicate daily bar found for {symbol} on {d}",
                            "trading_date": d,
                        }
                    )
                seen_dates.add(d)

        # Check missing sessions
        start_date = sorted_bars[0]["trading_date"]
        end_date = sorted_bars[-1]["trading_date"]
        expected_sessions = self.calendar.sessions_between(start_date, end_date)
        for s in expected_sessions:
            if s not in dates_present:
                alerts.append(
                    {
                        "level": "WARNING",
                        "category": "missing_session",
                        "message": f"Missing expected trading session for {symbol} on {s}",
                        "trading_date": s,
                    }
                )

        # Check OHLC invariants
        for b in sorted_bars:
            d = b["trading_date"]
            o = b["open"]
            h = b["high"]
            lo = b["low"]
            c = b["close"]
            v = b["volume"]

            # Negative values check
            if o < 0 or h < 0 or lo < 0 or c < 0:
                alerts.append(
                    {
                        "level": "CRITICAL",
                        "category": "negative_values",
                        "message": f"Negative price values found for {symbol} on {d}: O={o}, H={h}, L={lo}, C={c}",
                        "trading_date": d,
                    }
                )

            if v < 0:
                alerts.append(
                    {
                        "level": "ERROR",
                        "category": "negative_values",
                        "message": f"Negative volume found for {symbol} on {d}: V={v}",
                        "trading_date": d,
                    }
                )

            if v == 0:
                alerts.append(
                    {
                        "level": "WARNING",
                        "category": "negative_values",
                        "message": f"Zero volume recorded for active stock {symbol} on {d}",
                        "trading_date": d,
                    }
                )

            # OHLC logic check
            if h < o or h < c or h < lo:
                alerts.append(
                    {
                        "level": "CRITICAL",
                        "category": "ohlc_invalid",
                        "message": f"Invalid High price relation for {symbol} on {d}: High={h} is less than O={o}, L={lo}, or C={c}",
                        "trading_date": d,
                    }
                )

            if lo > o or lo > c:
                alerts.append(
                    {
                        "level": "CRITICAL",
                        "category": "ohlc_invalid",
                        "message": f"Invalid Low price relation for {symbol} on {d}: Low={lo} is greater than O={o} or C={c}",
                        "trading_date": d,
                    }
                )

        # Check for suspicious returns (> 20% single day)
        for i in range(1, len(sorted_bars)):
            prev_close = sorted_bars[i - 1]["close"]
            curr_close = sorted_bars[i]["close"]
            curr_date = sorted_bars[i]["trading_date"]

            if prev_close > 0:
                ret = abs((curr_close - prev_close) / prev_close)
                if ret > Decimal("0.20"):
                    alerts.append(
                        {
                            "level": "WARNING",
                            "category": "suspicious_return",
                            "message": f"Extreme daily return detected for {symbol} on {curr_date}: {ret * 100:.2f}%",
                            "trading_date": curr_date,
                        }
                    )

        # Check for stale data (last bar older than expected latest trading session)
        today = date.today()
        # Find latest trading day before or equal to today
        latest_trading_day = today
        if not self.calendar.is_trading_day(latest_trading_day):
            latest_trading_day = self.calendar.previous_trading_day(latest_trading_day)

        if end_date < latest_trading_day:
            delta = (latest_trading_day - end_date).days
            if delta > 3:  # Allow weekends/holidays gap safely
                alerts.append(
                    {
                        "level": "WARNING",
                        "category": "stale",
                        "message": f"Data for {symbol} is stale. Latest date is {end_date}, expected {latest_trading_day} (delta={delta} days)",
                        "trading_date": end_date,
                    }
                )

        return alerts
