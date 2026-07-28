import json
import logging
import os
from datetime import date, timedelta

import exchange_calendars as ecals
import pandas as pd

from tradecraft.config import settings
from tradecraft.core.exceptions import CalendarError

logger = logging.getLogger(__name__)

# Paths for application-level custom overrides
HOLIDAYS_OVERRIDE_FILE = os.path.join(settings.DATA_DIR, "nse_holidays_override.json")
SPECIAL_SESSIONS_OVERRIDE_FILE = os.path.join(
    settings.DATA_DIR, "nse_special_sessions_override.json"
)


# Baseline known special sessions/Muhurat dates
BASELINE_SPECIAL_SESSIONS = {
    date(2024, 11, 1),
    date(2025, 10, 20),
    date(2026, 11, 8),
}


class NSETradingCalendar:
    """Authoritative NSE Trading Calendar implementation.

    Uses exchange_calendars XBOM as a convenience reference, overlaying
    custom application-level overrides for trading holidays, Muhurat sessions,
    and exceptional market closures.
    """

    def __init__(self, use_overrides: bool = True):
        try:
            self._ref_cal = ecals.get_calendar("XBOM")
        except Exception as e:
            raise CalendarError(f"Failed to load underlying reference calendar (XBOM): {e}")

        self.holidays_override: set[date] = set()
        self.special_sessions_override: set[date] = set(BASELINE_SPECIAL_SESSIONS)

        if use_overrides:
            self.load_overrides()

    def load_overrides(self) -> None:
        """Load holiday and session overrides from the local data directory."""
        # Ensure data directory exists
        os.makedirs(settings.DATA_DIR, exist_ok=True)

        # 1. Load Holidays Override
        if os.path.exists(HOLIDAYS_OVERRIDE_FILE):
            try:
                with open(HOLIDAYS_OVERRIDE_FILE) as f:
                    dates_list = json.load(f)
                    self.holidays_override = {date.fromisoformat(d) for d in dates_list}
                    logger.info(
                        f"Loaded {len(self.holidays_override)} holiday overrides from {HOLIDAYS_OVERRIDE_FILE}"
                    )
            except Exception as e:
                logger.error(f"Failed to load holidays override file: {e}")

        # 2. Load Special Sessions Override
        if os.path.exists(SPECIAL_SESSIONS_OVERRIDE_FILE):
            try:
                with open(SPECIAL_SESSIONS_OVERRIDE_FILE) as f:
                    dates_list = json.load(f)
                    self.special_sessions_override = {date.fromisoformat(d) for d in dates_list}
                    logger.info(
                        f"Loaded {len(self.special_sessions_override)} special session overrides from {SPECIAL_SESSIONS_OVERRIDE_FILE}"
                    )
            except Exception as e:
                logger.error(f"Failed to load special sessions override file: {e}")

    def add_holiday_override(self, d: date) -> None:
        """Add a holiday override (removes this day from trading days)."""
        self.holidays_override.add(d)
        if d in self.special_sessions_override:
            self.special_sessions_override.remove(d)

    def add_special_session_override(self, d: date) -> None:
        """Add a special trading session override (adds this day to trading days)."""
        self.special_sessions_override.add(d)
        if d in self.holidays_override:
            self.holidays_override.remove(d)

    def is_trading_day(self, d: date) -> bool:
        """Check if a date is an active trading session for NSE."""
        # 1. Check custom overrides first (application-level authority)
        if d in self.holidays_override:
            return False
        if d in self.special_sessions_override:
            return True

        # 2. Fall back to underlying reference calendar
        try:
            ts = pd.Timestamp(d)
            return bool(self._ref_cal.is_session(ts))
        except Exception:
            return False

    def previous_trading_day(self, d: date) -> date:
        """Get the previous trading day before the given date."""
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

        sessions = []
        curr = start
        while curr <= end:
            if self.is_trading_day(curr):
                sessions.append(curr)
            curr += timedelta(days=1)
        return sessions

    def verify_against_manifest(
        self, expected_holidays: set[date], expected_sessions: set[date]
    ) -> bool:
        """Verify the calendar calculations against an authoritative manifest.

        Returns True if validation passes, raises CalendarError if there is any mismatch.
        """
        errors = []
        for h in expected_holidays:
            if self.is_trading_day(h):
                errors.append(
                    f"Disagreement: Day {h} is expected to be a Holiday, but was marked as a Trading Day."
                )

        for s in expected_sessions:
            if not self.is_trading_day(s):
                errors.append(
                    f"Disagreement: Day {s} is expected to be a Trading Session (e.g. Muhurat), but was marked as a Holiday."
                )

        if errors:
            err_msg = "\n".join(errors)
            logger.error(f"Authoritative calendar disagreement detected:\n{err_msg}")
            raise CalendarError(
                f"Calendar verification failed. Disagreement with authoritative NSE data:\n{err_msg}"
            )

        logger.info("Authoritative calendar verification successful. Disagreement checks passed.")
        return True
