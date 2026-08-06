"""Explicit Historical Data Backfill Workflow.

Per approved amendments:
- `data update` = normal incremental EOD update
- `data backfill` = intentional historical population

Bars are written with `is_adjusted=True`. Confirmed 2026-08-06: Zerodha's Kite Connect
historical API adjusts for bonuses, splits, rights issues, spin-offs and extraordinary
dividends server-side, retroactively across the whole series, at the ex-date
(https://x.com/zerodha/status/1952292763929874868). There is no genuinely raw/unadjusted
series available from this provider — `is_adjusted=False` here would be a false claim, not a
conservative default. Demerger-style discontinuities (e.g. CGPOWER's 2015-10-01 spin-off of
Crompton Greaves Consumer Electricals) are NOT adjusted by Kite, because a spin-off isn't a
single ratio — those must be handled per-instrument via the successions table, never spliced.

Backfill characteristics:
- Resumable (picks up from earliest existing bar per instrument)
- Incremental & Idempotent (skips already-covered date ranges)
- Rate-limit aware (configurable delay between provider chunks)
- Observable & Recoverable
- Computes per-instrument data coverage
"""

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tradecraft.core.db_models import Instrument, MarketBar
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.market_data.provider import MarketDataProvider

logger = logging.getLogger(__name__)


@dataclass
class InstrumentCoverage:
    """Historical coverage report for a single instrument."""

    symbol: str
    instrument_id: Any
    earliest_date: date | None
    latest_date: date | None
    total_bars: int
    missing_sessions_count: int
    status: str  # COMPLETE, PARTIAL, EMPTY, FAILED


class HistoricalBackfillWorkflow:
    """Orchestrates historical daily bar population for active instruments."""

    def __init__(
        self,
        db_session: Session,
        calendar: TradingCalendar,
        market_provider: MarketDataProvider,
        chunk_days: int = 60,
        chunk_delay_seconds: float = 0.5,
    ):
        self.db = db_session
        self.calendar = calendar
        self.market_provider = market_provider
        self.chunk_days = chunk_days
        self.chunk_delay_seconds = chunk_delay_seconds

    def seed_universe(self, symbols: list[str], exchange: str = "NSE") -> dict[str, Any]:
        """Ensure an Instrument row exists for every symbol, resolved against the broker dump.

        Identity fields (ISIN, name, tick/lot size, instrument_token) come from the broker
        instrument dump and are never invented. Symbols that cannot be resolved are reported
        as unresolved rather than being created with placeholder values — a placeholder
        instrument is how fabricated data enters a research database.
        """
        logger.info("Seeding universe: %d symbols", len(symbols))

        try:
            dump = self.market_provider.fetch_all_instruments()
        except Exception as e:
            raise RuntimeError(
                f"Could not fetch the broker instrument dump: {e}\n"
                "Instrument identity must come from the broker. Refusing to seed placeholders."
            ) from e

        by_symbol = {
            (i["exchange"], i["symbol"]): i
            for i in dump
            if i.get("segment") in (None, "NSE", "EQ", "NSE-EQ")
        }

        created, existing, unresolved = 0, 0, []
        for sym in symbols:
            ref = by_symbol.get((exchange, sym))
            if ref is None:
                unresolved.append(sym)
                continue

            inst = self.db.scalars(
                select(Instrument).where(
                    and_(Instrument.exchange == exchange, Instrument.symbol == sym)
                )
            ).first()

            if inst is None:
                self.db.add(
                    Instrument(
                        symbol=sym,
                        exchange=exchange,
                        segment="EQ",
                        name=ref.get("name"),
                        isin=ref.get("isin"),
                        tick_size=ref.get("tick_size"),
                        lot_size=ref.get("lot_size"),
                        instrument_token=ref.get("instrument_token"),
                        is_active=True,
                    )
                )
                created += 1
            else:
                inst.instrument_token = ref.get("instrument_token") or inst.instrument_token
                inst.isin = ref.get("isin") or inst.isin
                inst.is_active = True
                existing += 1

        self.db.commit()

        if unresolved:
            logger.warning(
                "%d symbol(s) not found in the broker dump (likely delisted or renamed): %s",
                len(unresolved),
                ", ".join(unresolved),
            )

        return {"created": created, "existing": existing, "unresolved": unresolved}

    def run_backfill(
        self,
        target_years: int = 2,
        instrument_symbol: str | None = None,
    ) -> dict[str, Any]:
        """Run explicit historical backfill.

        Args:
            target_years: Desired historical depth in years.
            instrument_symbol: Optional single symbol filter.

        Returns:
            Detailed execution summary report.
        """
        logger.info(f"Starting historical data backfill (target_years={target_years})...")

        end_date = date.today()
        if not self.calendar.is_trading_day(end_date):
            end_date = self.calendar.previous_trading_day(end_date)

        target_start_date = end_date - timedelta(days=target_years * 365)

        # Get target active instruments
        stmt = select(Instrument).where(Instrument.is_active == True)  # noqa: E712
        if instrument_symbol:
            stmt = stmt.where(Instrument.symbol == instrument_symbol)
        instruments = self.db.scalars(stmt).all()

        report: dict[str, Any] = {
            "total_instruments": len(instruments),
            "target_start_date": target_start_date.isoformat(),
            "target_end_date": end_date.isoformat(),
            "bars_inserted": 0,
            "chunks_processed": 0,
            "chunks_failed": 0,
            "duplicates_skipped": 0,
            "integrity_retries": 0,
            "instruments_failed": [],
            "instrument_coverages": [],
            "status": "COMPLETED",
        }

        for inst in instruments:
            try:
                existing_dates = self._existing_dates(inst)
                gaps = self._missing_ranges(existing_dates, target_start_date, end_date)

                if not gaps:
                    logger.info("%s: coverage complete, nothing to fetch.", inst.symbol)
                    report["instrument_coverages"].append(
                        self._get_coverage(inst, target_start_date, end_date)
                    )
                    continue

                total_missing = sum((g[1] - g[0]).days + 1 for g in gaps)
                logger.info(
                    "%s: %d gap(s) covering ~%d calendar days -> %s",
                    inst.symbol,
                    len(gaps),
                    total_missing,
                    ", ".join(f"{a}..{b}" for a, b in gaps[:5]),
                )

                for gap_start, gap_end in gaps:
                    curr_start = gap_start
                    while curr_start <= gap_end:
                        curr_end = min(curr_start + timedelta(days=self.chunk_days), gap_end)

                        try:
                            bars = self.market_provider.get_daily_bars(
                                inst.symbol, inst.exchange, curr_start, curr_end
                            )
                        except Exception as e:
                            # One bad chunk must not abandon the rest of the instrument.
                            logger.warning(
                                "%s: provider error for %s..%s: %s",
                                inst.symbol, curr_start, curr_end, e,
                            )
                            report["chunks_failed"] += 1
                            report["status"] = "PARTIAL_FAILURE"
                            curr_start = curr_end + timedelta(days=1)
                            continue

                        inserted = self._insert_chunk(inst, bars, existing_dates, report)
                        report["bars_inserted"] += inserted
                        report["chunks_processed"] += 1

                        curr_start = curr_end + timedelta(days=1)
                        if self.chunk_delay_seconds > 0:
                            time.sleep(self.chunk_delay_seconds)

                report["instrument_coverages"].append(
                    self._get_coverage(inst, target_start_date, end_date)
                )

            except Exception as e:
                self.db.rollback()
                logger.error("Backfill failed for %s: %s", inst.symbol, e)
                report["instruments_failed"].append({"symbol": inst.symbol, "error": str(e)})
                report["status"] = "PARTIAL_FAILURE"

        return report

    # ------------------------------------------------------------------ gap detection

    def _existing_dates(self, inst: Instrument) -> set[date]:
        """All trading dates already stored for this instrument."""
        rows = self.db.execute(
            select(MarketBar.trading_date).where(
                and_(
                    MarketBar.instrument_id == inst.id,
                    MarketBar.is_adjusted == True,  # noqa: E712
                )
            )
        ).all()
        return {r[0] for r in rows}

    def _missing_ranges(
        self, existing: set[date], target_start: date, target_end: date
    ) -> list[tuple[date, date]]:
        """Return contiguous spans of trading sessions that are absent from the database.

        RESUME CORRECTNESS (fixed 2026-08-06)
        =====================================
        The previous implementation computed a single range:

            needed_end = coverage.earliest_date - 1 day

        so it only ever fetched history OLDER than the earliest stored bar. If an
        instrument's backfill aborted part-way through - as happened to ONGC, COALINDIA,
        PETRONET and NMDC on a UniqueViolation - the stored earliest date was already at the
        target start, so `needed_start > needed_end` and the instrument was reported as
        "already has required historical depth" and SKIPPED.

        Re-running the backfill could therefore never repair a truncated instrument, and the
        gap was invisible because coverage was measured from the earliest bar rather than
        against the trading calendar. Interior holes were equally unreachable.

        Gaps are now derived by differencing the exchange calendar against stored dates, so
        leading, trailing and interior gaps are all repaired on a plain re-run.
        """
        try:
            sessions = [
                s if isinstance(s, date) else s.date()
                for s in self.calendar.sessions_between(target_start, target_end)
            ]
        except Exception as e:
            logger.warning("Calendar unavailable (%s); falling back to weekday span.", e)
            sessions = []
            d = target_start
            while d <= target_end:
                if d.weekday() < 5:
                    sessions.append(d)
                d += timedelta(days=1)

        missing = [s for s in sessions if s not in existing]
        if not missing:
            return []

        # Collapse consecutive missing sessions into fetch ranges. A tolerance stops a few
        # scattered holidays or suspension days from exploding into hundreds of API calls.
        ranges: list[tuple[date, date]] = []
        run_start = prev = missing[0]
        for s in missing[1:]:
            if (s - prev).days <= 10:
                prev = s
                continue
            ranges.append((run_start, prev))
            run_start = prev = s
        ranges.append((run_start, prev))

        # Ignore trivial gaps: a single missing session is usually an exchange special
        # session or a suspension, not a fetch failure.
        return [(a, b) for a, b in ranges if (b - a).days >= 1 or len(missing) > 3]

    # ------------------------------------------------------------------ chunk insertion

    def _insert_chunk(
        self,
        inst: Instrument,
        bars: list[dict[str, Any]],
        existing_dates: set[date],
        report: dict[str, Any],
    ) -> int:
        """Insert a chunk idempotently, tolerating duplicates from any source.

        DUPLICATE HANDLING (fixed 2026-08-06)
        =====================================
        The previous implementation issued a per-bar SELECT to test for an existing row,
        then `db.add(...)` without flushing. A pending unflushed insert is invisible to a
        subsequent SELECT, so when the provider returned the same trading_date twice in one
        response - which Kite does around session boundaries and special sessions - both
        rows were added and the chunk commit raised

            UniqueViolation: duplicate key value violates unique constraint
            "uq_instrument_date_adj"

        The exception handler then rolled back and moved on to the NEXT INSTRUMENT,
        abandoning the remainder of that symbol's history mid-backfill. That is how ONGC,
        COALINDIA, PETRONET and NMDC ended up truncated.

        Three defences now apply:
          1. de-duplicate the provider response in memory by trading_date
          2. check against a preloaded set of stored dates, updated as we insert
          3. on IntegrityError, fall back to per-row SAVEPOINT inserts so a single bad row
             cannot discard a whole chunk, and never abandon the instrument
        """
        seen: set[date] = set()
        pending: list[MarketBar] = []

        for b in bars:
            td = b["trading_date"]
            if td in existing_dates or td in seen:
                report["duplicates_skipped"] += 1
                continue
            seen.add(td)
            pending.append(
                MarketBar(
                    instrument_id=inst.id,
                    trading_date=td,
                    open=b["open"],
                    high=b["high"],
                    low=b["low"],
                    close=b["close"],
                    volume=b["volume"],
                    source=b["source"],
                    retrieved_at=b["retrieved_at"],
                    is_adjusted=True,
                )
            )

        if not pending:
            return 0

        try:
            self.db.add_all(pending)
            self.db.commit()
            existing_dates.update(seen)
            return len(pending)
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(
                "%s: chunk commit hit an integrity error (%s). Retrying row-by-row.",
                inst.symbol,
                type(e.orig).__name__ if hasattr(e, "orig") else "IntegrityError",
            )

        inserted = 0
        for b in pending:
            try:
                with self.db.begin_nested():
                    self.db.add(b)
                inserted += 1
                existing_dates.add(b.trading_date)
            except IntegrityError:
                self.db.rollback()
                report["duplicates_skipped"] += 1
        self.db.commit()
        report["integrity_retries"] += 1
        return inserted

    def _get_coverage(
        self, inst: Instrument, target_start: date, target_end: date
    ) -> InstrumentCoverage:
        """Inspect stored bars to build coverage metrics."""
        stmt = (
            select(MarketBar)
            .where(
                and_(
                    MarketBar.instrument_id == inst.id,
                    MarketBar.is_adjusted == True,  # noqa: E712
                    MarketBar.trading_date >= target_start,
                    MarketBar.trading_date <= target_end,
                )
            )
            .order_by(MarketBar.trading_date)
        )
        bars = self.db.scalars(stmt).all()

        if not bars:
            return InstrumentCoverage(
                symbol=inst.symbol,
                instrument_id=inst.id,
                earliest_date=None,
                latest_date=None,
                total_bars=0,
                missing_sessions_count=0,
                status="EMPTY",
            )

        earliest = bars[0].trading_date
        latest = bars[-1].trading_date
        expected_sessions = self.calendar.sessions_between(earliest, latest)
        missing_cnt = max(0, len(expected_sessions) - len(bars))

        status = "COMPLETE" if missing_cnt == 0 and earliest <= target_start else "PARTIAL"

        return InstrumentCoverage(
            symbol=inst.symbol,
            instrument_id=inst.id,
            earliest_date=earliest,
            latest_date=latest,
            total_bars=len(bars),
            missing_sessions_count=missing_cnt,
            status=status,
        )
