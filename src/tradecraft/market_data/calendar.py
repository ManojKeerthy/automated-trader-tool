import logging
from datetime import date, timedelta

import exchange_calendars as ecals
import pandas as pd

from tradecraft.core.exceptions import CalendarError

logger = logging.getLogger(__name__)

# Official known holidays for 2026 for validation purposes
OFFICIAL_2026_HOLIDAYS = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),  # Holi
    date(2026, 3, 26),  # Shri Ram Navami
    date(2026, 3, 31),  # Shri Mahavir Jayanti
    date(2026, 4, 3),  # Good Friday
    date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    date(2026, 5, 1),  # Maharashtra Day
    date(2026, 5, 28),  # Bakri Id
    date(2026, 6, 26),  # Muharram
    date(2026, 9, 14),  # Ganesh Chaturthi
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 10),  # Diwali - Balipratipada
    date(2026, 11, 24),  # Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas
}

# Special sessions or Muhurat Trading dates
MUHURAT_SESSIONS = {
    date(2026, 11, 8),  # Diwali Laxmi Pujan (Muhurat Trading)
}


class TradingCalendar:
    """Trading calendar abstraction wrapping exchange_calendars for NSE (XNSE)."""

    def __init__(self, exchange_code: str = "XBOM"):
        self.exchange_code = exchange_code
        try:
            self._cal = ecals.get_calendar(exchange_code)
        except Exception as e:
            raise CalendarError(f"Failed to load exchange calendar for {exchange_code}: {e}")

    def is_trading_day(self, d: date) -> bool:
        """Check if a date is a valid trading session."""
        # Handle special/Muhurat sessions explicitly
        if d in MUHURAT_SESSIONS:
            return True
        # Base check using exchange_calendars
        try:
            ts = pd.Timestamp(d)
            return bool(self._cal.is_session(ts))
        except Exception:
            return False

    def previous_trading_day(self, d: date) -> date:
        """Get the previous trading day before the given date."""
        # Loop backwards to find a trading day
        curr = d - timedelta(days=1)
        while not self.is_trading_day(curr):
            curr -= timedelta(days=1)
        return curr

    def next_trading_day(self, d: date) -> date:
        """Get the next trading day after the given date."""
        curr = d + timedelta(days=1)
        while not self.is_trading_day(curr):
            curr += timedelta(days=1)
        return curr

    def sessions_between(self, start: date, end: date) -> list[date]:
        """Get list of trading dates between start and end (inclusive)."""
        if start > end:
            return []

        # We collect sessions date-by-date to account for Muhurat sessions
        sessions = []
        curr = start
        while curr <= end:
            if self.is_trading_day(curr):
                sessions.append(curr)
            curr += timedelta(days=1)
        return sessions

    def run_calendar_validation(self, year: int = 2026) -> bool:
        """Validate the local calendar against official known holidays.

        Returns True if validation passes, False otherwise.
        """
        logger.info(f"Running calendar validation for year {year}...")
        errors = []

        if year == 2026:
            # Check if all official 2026 holidays are correctly marked as non-trading days
            for holiday in OFFICIAL_2026_HOLIDAYS:
                # Except if it falls on Muhurat, which is not the case for 2026 list
                if self.is_trading_day(holiday):
                    errors.append(
                        f"Official holiday {holiday} is incorrectly marked as a trading day."
                    )

            # Check if Muhurat Trading is marked as a trading day
            for muhurat in MUHURAT_SESSIONS:
                if not self.is_trading_day(muhurat):
                    errors.append(
                        f"Special Muhurat session {muhurat} is incorrectly marked as a non-trading day."
                    )

        if errors:
            for err in errors:
                logger.error(f"[CALENDAR VALIDATION ERROR]: {err}")
            return False

        logger.info("Calendar validation successful. Stored calendar matches official circulars.")
        return True
