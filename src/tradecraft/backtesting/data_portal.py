"""Point-in-time data portal for backtesting.

The DataPortal is the ONLY interface through which strategies access
market data during a backtest. It enforces that no data beyond the
current simulation date can be accessed.

Look-ahead protection is enforced at multiple levels:
1. Date boundary check on all queries
2. Pre-loaded data is filtered to prevent accidental leakage
3. Feature alignment is capped at the current clock date
4. Universe membership queries are gated
5. Benchmark data is gated

Any violation raises LookAheadError.
"""

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from tradecraft.core.db_models import Instrument, MarketBar
from tradecraft.core.exceptions import LookAheadError
from tradecraft.instruments.universe import PointInTimeUniverse

logger = logging.getLogger(__name__)


class DataPortal:
    """Point-in-time market data interface for backtesting.

    Strategies access data exclusively through this portal. The portal
    enforces that no data beyond `_current_date` is ever returned.

    Data is pre-loaded from the database for the backtest period to
    avoid per-bar database queries, but all returned data is filtered
    to the current simulation date.
    """

    def __init__(
        self,
        db_session: Session,
        universe: PointInTimeUniverse,
        start_date: date,
        end_date: date,
    ):
        self._db = db_session
        self._universe = universe
        self._start_date = start_date
        self._end_date = end_date
        self._current_date: date | None = None

        # Pre-loaded data cache: instrument_id -> sorted list of bar dicts
        self._bars_cache: dict[uuid.UUID, list[dict[str, Any]]] = {}
        # Instrument lookup cache
        self._instruments: dict[uuid.UUID, Instrument] = {}

    def preload(self, instrument_ids: list[uuid.UUID]) -> None:
        """Pre-load market data from DB for performance.

        Data is loaded up to `_end_date` but access is still gated
        by `_current_date` on every query.
        """
        logger.info(f"Pre-loading market data for {len(instrument_ids)} instruments...")

        for inst_id in instrument_ids:
            # Load instrument
            inst = self._db.get(Instrument, inst_id)
            if inst:
                self._instruments[inst_id] = inst

            # Load raw bars (not adjusted) for the full backtest period
            stmt = (
                select(MarketBar)
                .where(
                    and_(
                        MarketBar.instrument_id == inst_id,
                        MarketBar.is_adjusted == False,  # noqa: E712
                        MarketBar.trading_date <= self._end_date,
                    )
                )
                .order_by(MarketBar.trading_date)
            )
            bars = self._db.scalars(stmt).all()

            self._bars_cache[inst_id] = [
                {
                    "trading_date": b.trading_date,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in bars
            ]

        logger.info(f"Pre-loaded data for {len(self._bars_cache)} instruments")

    def set_current_date(self, dt: date) -> None:
        """Advance the portal clock. Called by the BacktestEngine each session."""
        if self._current_date is not None and dt <= self._current_date:
            raise ValueError(f"Cannot move clock backwards: {dt} <= {self._current_date}")
        self._current_date = dt

    def _check_date(self, requested_date: date) -> None:
        """Guard: raise LookAheadError if requested date exceeds current clock."""
        if self._current_date is None:
            raise LookAheadError("DataPortal clock not initialized — call set_current_date first")
        if requested_date > self._current_date:
            raise LookAheadError(
                f"Look-ahead detected: requested data for {requested_date} "
                f"but current simulation date is {self._current_date}"
            )

    def get_bars(
        self,
        instrument_id: uuid.UUID,
        end_date: date,
        lookback: int | None = None,
    ) -> pd.DataFrame:
        """Get historical bars up to and including `end_date`.

        Args:
            instrument_id: Instrument UUID
            end_date: Latest date to include (must be <= current clock date)
            lookback: Optional max number of bars to return (most recent N)

        Returns:
            DataFrame with columns: trading_date, open, high, low, close, volume
            Indexed by trading_date, sorted ascending.

        Raises:
            LookAheadError: If end_date > current simulation date
        """
        self._check_date(end_date)

        all_bars = self._bars_cache.get(instrument_id, [])
        # Filter to bars <= end_date (point-in-time enforcement)
        filtered = [b for b in all_bars if b["trading_date"] <= end_date]

        if lookback is not None and lookback > 0:
            filtered = filtered[-lookback:]

        if not filtered:
            return pd.DataFrame(columns=["trading_date", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(filtered)
        df = df.set_index("trading_date")
        return df

    def get_history(
        self,
        instrument_id: uuid.UUID,
        end_date: date,
        count: int,
    ) -> list[dict[str, Any]]:
        """Get historical bars as a list of bar dicts up to and including end_date.

        Raises LookAheadError if end_date > current clock date.
        """
        self._check_date(end_date)
        all_bars = self._bars_cache.get(instrument_id, [])
        filtered = [b for b in all_bars if b["trading_date"] <= end_date]
        if count > 0:
            filtered = filtered[-count:]
        return [dict(b) for b in filtered]

    def get_close(self, instrument_id: uuid.UUID, query_date: date) -> Decimal | None:
        """Get closing price at a specific date.

        Raises LookAheadError if query_date > current clock date.
        """
        self._check_date(query_date)

        all_bars = self._bars_cache.get(instrument_id, [])
        for b in all_bars:
            if b["trading_date"] == query_date:
                c_val = b["close"]
                return Decimal(str(c_val)) if c_val is not None else None
        return None

    def get_bar(self, instrument_id: uuid.UUID, query_date: date) -> dict[str, Any] | None:
        """Get full OHLCV bar at a specific date.

        Raises LookAheadError if query_date > current clock date.
        """
        self._check_date(query_date)

        all_bars = self._bars_cache.get(instrument_id, [])
        for b in all_bars:
            if b["trading_date"] == query_date:
                return dict(b)
        return None

    def get_latest_close(self, instrument_id: uuid.UUID) -> Decimal | None:
        """Get the most recent close price as of current simulation date."""
        if self._current_date is None:
            raise LookAheadError("DataPortal clock not initialized")

        all_bars = self._bars_cache.get(instrument_id, [])
        # Find latest bar at or before current date
        latest = None
        for b in all_bars:
            if b["trading_date"] <= self._current_date:
                latest = b
        if latest and latest["close"] is not None:
            return Decimal(str(latest["close"]))
        return None

    def get_universe_members(self, query_date: date) -> list[Instrument]:
        """Get universe members at a point in time.

        Raises LookAheadError if query_date > current clock date.
        """
        self._check_date(query_date)
        return self._universe.member_instruments(query_date)

    def get_universe_confidence(self, query_date: date) -> str:
        """Get confidence level of universe membership at query_date."""
        self._check_date(query_date)
        return self._universe.membership_confidence(query_date)

    def get_instrument(self, instrument_id: uuid.UUID) -> Instrument | None:
        """Get instrument metadata (non-temporal, always available)."""
        return self._instruments.get(instrument_id)

    def has_data(self, instrument_id: uuid.UUID, query_date: date) -> bool:
        """Check if data exists for an instrument at a specific date."""
        self._check_date(query_date)
        all_bars = self._bars_cache.get(instrument_id, [])
        return any(b["trading_date"] == query_date for b in all_bars)

    def get_data_coverage(self, instrument_id: uuid.UUID) -> dict[str, Any]:
        """Get data coverage info for an instrument (up to current date)."""
        if self._current_date is None:
            raise LookAheadError("DataPortal clock not initialized")

        all_bars = self._bars_cache.get(instrument_id, [])
        available = [b for b in all_bars if b["trading_date"] <= self._current_date]

        if not available:
            return {"bar_count": 0, "earliest": None, "latest": None}

        return {
            "bar_count": len(available),
            "earliest": available[0]["trading_date"],
            "latest": available[-1]["trading_date"],
        }
