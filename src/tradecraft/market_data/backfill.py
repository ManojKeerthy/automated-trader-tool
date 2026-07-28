"""Explicit Historical Data Backfill Workflow.

Per approved amendments:
- `data update` = normal incremental EOD update
- `data backfill` = intentional historical population

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
            "instrument_coverages": [],
            "status": "COMPLETED",
        }

        for inst in instruments:
            try:
                # Inspect existing coverage
                coverage = self._get_coverage(inst, target_start_date, end_date)

                # Determine missing historical range
                needed_start = target_start_date
                needed_end = coverage.earliest_date - timedelta(days=1) if coverage.earliest_date else end_date

                if needed_start > needed_end:
                    logger.info(f"Instrument {inst.symbol} already has required historical depth.")
                    report["instrument_coverages"].append(coverage)
                    continue

                logger.info(
                    f"Backfilling {inst.symbol} from {needed_start} to {needed_end}..."
                )

                # Process in chunks to respect provider limits
                curr_start = needed_start
                while curr_start <= needed_end:
                    curr_end = min(curr_start + timedelta(days=self.chunk_days), needed_end)

                    bars = self.market_provider.get_daily_bars(
                        inst.symbol, inst.exchange, curr_start, curr_end
                    )

                    inserted_this_chunk = 0
                    for b_data in bars:
                        # Avoid duplicates
                        existing = self.db.scalars(
                            select(MarketBar).where(
                                and_(
                                    MarketBar.instrument_id == inst.id,
                                    MarketBar.trading_date == b_data["trading_date"],
                                    MarketBar.is_adjusted == False,  # noqa: E712
                                )
                            )
                        ).first()

                        if not existing:
                            bar = MarketBar(
                                instrument_id=inst.id,
                                trading_date=b_data["trading_date"],
                                open=b_data["open"],
                                high=b_data["high"],
                                low=b_data["low"],
                                close=b_data["close"],
                                volume=b_data["volume"],
                                source=b_data["source"],
                                retrieved_at=b_data["retrieved_at"],
                                is_adjusted=False,
                            )
                            self.db.add(bar)
                            inserted_this_chunk += 1

                    self.db.commit()
                    report["bars_inserted"] += inserted_this_chunk
                    report["chunks_processed"] += 1

                    curr_start = curr_end + timedelta(days=1)
                    if self.chunk_delay_seconds > 0:
                        time.sleep(self.chunk_delay_seconds)

                # Re-check updated coverage
                final_cov = self._get_coverage(inst, target_start_date, end_date)
                report["instrument_coverages"].append(final_cov)

            except Exception as e:
                self.db.rollback()
                logger.error(f"Backfill failed for {inst.symbol}: {e}")
                report["status"] = "PARTIAL_FAILURE"

        return report

    def _get_coverage(self, inst: Instrument, target_start: date, target_end: date) -> InstrumentCoverage:
        """Inspect stored bars to build coverage metrics."""
        stmt = (
            select(MarketBar)
            .where(
                and_(
                    MarketBar.instrument_id == inst.id,
                    MarketBar.is_adjusted == False,  # noqa: E712
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
