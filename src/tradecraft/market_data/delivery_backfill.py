"""Historical backfill for NSE delivery-position data (see delivery_provider.py for source
details and file-format notes).

Mirrors HistoricalBackfillWorkflow's design: resumable, idempotent, rate-limit aware,
observable. Symbol matching is direct current-symbol only, deliberately not chain-resolved
through historical renames/mergers - see `_build_symbol_to_instrument_map` for why.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from tradecraft.core.db_models import DeliveryPosition, Instrument
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.market_data.delivery_provider import fetch_mto_file

logger = logging.getLogger("tradecraft.delivery_backfill")


@dataclass
class DeliveryBackfillReport:
    start_date: date
    end_date: date
    trading_days_processed: int = 0
    trading_days_with_data: int = 0
    records_written: int = 0
    records_already_present: int = 0
    fetch_errors: list[str] = field(default_factory=list)


def _build_symbol_to_instrument_map(db: Session) -> dict[str, Instrument]:
    """Map an MTO row's symbol, as-is, to its Instrument - direct current-symbol match only.

    Deliberately does NOT walk SYMBOL_SUCCESSION chains. A first attempt at this spliced
    pre-merger symbols (e.g. "HDFC") onto the surviving/successor instrument ("HDFCBANK"),
    tried against a real 2016 file, and produced two distinct companies' delivery rows
    colliding on one instrument_id on the same day (HDFC + HDFCBANK were separate, both-listed
    companies until their 2023 merger) - a UNIQUE constraint violation caught this, but the
    underlying problem is a correctness one, not just a DB-constraint one: SYMBOL_SUCCESSION
    mixes pure renames (safe to splice) with mergers/demergers (NOT safe - the old symbol is a
    genuinely different legal entity with its own history, splicing it creates a fictitious
    continuous series, precisely what this project's own standing rules warn against, e.g.
    universes.py's notes on TATAMOTORS/PEL). Rather than hand-classify which entries are
    "safe," direct-match only: an instrument that changed its literal ticker symbol simply has
    a delivery-data gap before that change, which is honest (unmeasurable is not zero), not a
    silently wrong number.
    """
    instruments = list(db.scalars(select(Instrument)).all())
    return {inst.symbol.strip().upper(): inst for inst in instruments}


def run_delivery_backfill(
    db: Session,
    calendar: TradingCalendar,
    start_date: date,
    end_date: date,
    request_delay_seconds: float = 0.3,
) -> DeliveryBackfillReport:
    """Backfill delivery positions for every tradeable session in [start_date, end_date].

    Idempotent: a session already fully covered (every mapped symbol already has a
    DeliveryPosition row for that date) is fetched again only to confirm coverage is complete,
    not to re-fetch already-written rows (the DB unique constraint would reject duplicates
    regardless, but skipping known-present rows avoids needless work on resume).
    """
    report = DeliveryBackfillReport(start_date=start_date, end_date=end_date)
    symbol_map = _build_symbol_to_instrument_map(db)
    logger.info("Symbol map built: %d resolvable symbols (current + historical)", len(symbol_map))

    http_session = requests.Session()

    sessions = calendar.sessions_between(start_date, end_date)
    logger.info("Backfilling delivery data for %d trading sessions", len(sessions))

    for i, trading_date in enumerate(sessions):
        report.trading_days_processed += 1

        result = fetch_mto_file(trading_date, session=http_session)
        if result.error:
            report.fetch_errors.append(f"{trading_date}: {result.error}")
            logger.warning("Fetch error for %s: %s", trading_date, result.error)
            time.sleep(request_delay_seconds)
            continue
        if not result.found:
            time.sleep(request_delay_seconds)
            continue

        report.trading_days_with_data += 1

        existing_rows = db.scalars(
            select(DeliveryPosition.instrument_id).where(
                DeliveryPosition.trading_date == trading_date
            )
        ).all()
        already_present_ids = set(existing_rows)

        for rec in result.records:
            inst = symbol_map.get(rec.symbol.strip().upper())
            if inst is None:
                continue
            if inst.id in already_present_ids:
                report.records_already_present += 1
                continue
            db.add(
                DeliveryPosition(
                    instrument_id=inst.id,
                    trading_date=trading_date,
                    traded_qty=rec.traded_qty,
                    delivery_qty=rec.delivery_qty,
                    delivery_pct=Decimal(str(rec.delivery_pct)),
                    source="NSE_MTO",
                )
            )
            report.records_written += 1

        db.commit()

        if (i + 1) % 100 == 0:
            logger.info(
                "Progress: %d/%d sessions, %d records written so far",
                i + 1,
                len(sessions),
                report.records_written,
            )

        time.sleep(request_delay_seconds)

    logger.info(
        "Delivery backfill complete: %d/%d sessions had data, %d records written, %d errors",
        report.trading_days_with_data,
        report.trading_days_processed,
        report.records_written,
        len(report.fetch_errors),
    )
    return report
