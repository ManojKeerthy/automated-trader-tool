"""Historical clock for deterministic backtesting.

The clock iterates through trading calendar sessions one at a time,
enforcing chronological progression. No random access to dates is
permitted — the backtest must travel through history sequentially.
"""

from datetime import date

from tradecraft.market_data.calendar import TradingCalendar


class HistoricalClock:
    """Chronological trading session iterator for backtesting.

    Yields one trading date at a time in order, ensuring the
    backtest engine processes history sequentially.
    """

    def __init__(self, calendar: TradingCalendar, start_date: date, end_date: date):
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")
        self._calendar = calendar
        self._start_date = start_date
        self._end_date = end_date
        self._sessions = calendar.sessions_between(start_date, end_date)
        self._current_index = -1
        self._current_date: date | None = None

    @property
    def current_date(self) -> date | None:
        """The current simulation date, or None if not started."""
        return self._current_date

    @property
    def sessions(self) -> list[date]:
        """All trading sessions in this clock's range."""
        return list(self._sessions)

    @property
    def total_sessions(self) -> int:
        return len(self._sessions)

    def __iter__(self) -> "HistoricalClock":
        self._current_index = -1
        self._current_date = None
        return self

    def __next__(self) -> date:
        self._current_index += 1
        if self._current_index >= len(self._sessions):
            raise StopIteration
        self._current_date = self._sessions[self._current_index]
        return self._current_date

    def __len__(self) -> int:
        return len(self._sessions)
