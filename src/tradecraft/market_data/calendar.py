import json
import logging
from datetime import date
from pathlib import Path

from tradecraft.market_data.nse_calendar import NSETradingCalendar

logger = logging.getLogger(__name__)


class TradingCalendar:
    """Trading calendar abstraction.

    Acts as the primary interface for market scheduling, delegating to the
    application-level custom NSETradingCalendar.
    """

    def __init__(self) -> None:
        self._calendar = NSETradingCalendar()

    def is_trading_day(self, d: date) -> bool:
        """Check if a date is a valid trading session."""
        return self._calendar.is_trading_day(d)

    def previous_trading_day(self, d: date) -> date:
        """Get the previous trading day before the given date."""
        return self._calendar.previous_trading_day(d)

    def next_trading_day(self, d: date) -> date:
        """Get the next trading day after the given date."""
        return self._calendar.next_trading_day(d)

    def sessions_between(self, start: date, end: date) -> list[date]:
        """Get list of trading dates between start and end (inclusive)."""
        return self._calendar.sessions_between(start, end)

    def run_calendar_validation(self, year: int = 2026) -> bool:
        """Validate the local calendar calculations against a regression fixture manifest.

        Returns True if validation passes, False otherwise.
        """
        logger.info(f"Running calendar validation for year {year}...")

        # Locate the regression fixture file for the given year
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        fixture_path = base_dir / "tests" / "fixtures" / f"calendar_{year}_regression.json"

        if not fixture_path.exists():
            logger.warning(
                f"No calendar regression manifest found at {fixture_path}. Skipping validation."
            )
            return True

        try:
            with open(fixture_path) as f:
                data = json.load(f)

            expected_holidays = {date.fromisoformat(d) for d in data.get("holidays", [])}
            expected_sessions = {date.fromisoformat(d) for d in data.get("special_sessions", [])}

            return self._calendar.verify_against_manifest(expected_holidays, expected_sessions)
        except Exception as e:
            logger.error(f"[CALENDAR VALIDATION ERROR]: {e}")
            return False
