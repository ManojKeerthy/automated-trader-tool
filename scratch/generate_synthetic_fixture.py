"""SYNTHETIC MARKET DATA FIXTURE GENERATOR — NOT REAL MARKET DATA.

================================================================================
!!  DANGER  !!  THIS SCRIPT FABRICATES PRICES. IT DOES NOT FETCH THEM.
================================================================================

This module previously lived at `scratch/seed_real_market_bars.py` and stamped every
generated bar with `source = "ZERODHA_KITE_EOD"`. That misnaming caused Research Cycles 1
and 2 to be conducted entirely against fabricated prices, invalidating ~250 governance
documents and two full research cycles.
See docs/research/REPO_AUDIT_2026-08-06.md.

What this generator actually produces:
  - A repeating 21-day sawtooth return series, IDENTICAL for every instrument
    (cross-sectional correlation = 1.0, so all relative-strength research is meaningless)
  - open == close on every single bar (high/low are fixed +/-1.2% bands around close)
  - A constant ATR of exactly 2.4% of price, forever
  - Volume as a monotonically increasing linear counter
  - Placeholder corporate actions (one identical dividend per instrument)

Expected gross edge for ANY trading rule on this series is exactly zero.

PERMITTED USE:
  Unit-test fixtures and engine plumbing checks ONLY.

PROHIBITED USE:
  Any hypothesis evaluation, any backtest whose result is reported, anything that writes
  to a database used for research.

Bars are stamped `source = "SYNTHETIC_FIXTURE"` and `is_adjusted = False` so that the data
authenticity gate (tests/integration/test_data_authenticity.py, enforced via
core/preflight.py) will reject any research database containing them.

Requires the explicit --i-understand-this-is-fake flag to run, and refuses to write to any
database path that does not contain "synthetic" or "fixture".
"""


import argparse
import logging
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from tradecraft.core.db_models import Base, CorporateAction, Instrument, MarketBar
from tradecraft.market_data.calendar import TradingCalendar

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("generate_synthetic_fixture")

SYNTHETIC_SECURITIES = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "isin": "INE002A01018", "base_price": 1200.0, "drift": 0.0004},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "isin": "INE467B01029", "base_price": 2000.0, "drift": 0.0003},
    {"symbol": "INFY", "name": "Infosys Ltd", "isin": "INE009A01021", "base_price": 700.0, "drift": 0.0005},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "isin": "INE040A01034", "base_price": 1100.0, "drift": 0.0002},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "isin": "INE090A01021", "base_price": 400.0, "drift": 0.0006},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "isin": "INE081A01020", "base_price": 350.0, "drift": 0.0003},
    {"symbol": "SBIN", "name": "State Bank of India", "isin": "INE062A01020", "base_price": 250.0, "drift": 0.0004},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "isin": "INE397D01024", "base_price": 380.0, "drift": 0.0005},
    {"symbol": "ITC", "name": "ITC Ltd", "isin": "INE154A01025", "base_price": 240.0, "drift": 0.0002},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "isin": "INE238A01034", "base_price": 500.0, "drift": 0.0004},
]


def seed_database(db_path: str) -> None:
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    calendar = TradingCalendar()
    start_dt = date(2016, 8, 1)
    end_dt = date(2024, 6, 30)

    trading_days = calendar.sessions_between(start_dt, end_dt)
    logger.info(f"Seeding {len(SYNTHETIC_SECURITIES)} securities across {len(trading_days)} trading sessions ({start_dt} to {end_dt})...")

    # 1. Seed Instruments
    inst_map = {}
    for s_info in SYNTHETIC_SECURITIES:
        stmt = select(Instrument).where(Instrument.symbol == s_info["symbol"])
        inst = session.scalars(stmt).first()
        if not inst:
            inst = Instrument(
                symbol=s_info["symbol"],
                name=s_info["name"],
                exchange="NSE",
                segment="EQ",
                isin=s_info["isin"],
                is_active=True,
            )
            session.add(inst)
            session.flush()
        inst_map[s_info["symbol"]] = inst

    # 2. Seed Corporate Actions
    ca_added = 0
    for s_symbol, inst in inst_map.items():
        stmt = select(CorporateAction).where(CorporateAction.instrument_id == inst.id)
        if not session.scalars(stmt).first():
            ca = CorporateAction(
                instrument_id=inst.id,
                action_type="DIVIDEND",
                ex_date=date(2021, 6, 15),
                record_date=date(2021, 6, 16),
                amount=Decimal("15.50"),
                source="SYNTHETIC_FIXTURE",
                verified=True,
            )
            session.add(ca)
            ca_added += 1

    # 3. Seed Historical Market Bars
    bars_added = 0
    now_utc = datetime.utcnow()

    for s_info in SYNTHETIC_SECURITIES:
        inst = inst_map[s_info["symbol"]]
        stmt = select(MarketBar).where(MarketBar.instrument_id == inst.id).limit(1)
        if session.scalars(stmt).first():
            logger.info(f"Market bars already present for {s_info['symbol']}, skipping...")
            continue

        curr_price = Decimal(str(s_info["base_price"]))
        drift = Decimal(str(s_info["drift"]))

        batch = []
        for idx, t_date in enumerate(trading_days):
            # Generate earnings announcement surge event every 40 days
            is_earnings_event = (idx > 20) and (idx % 40 == 0)
            if is_earnings_event:
                daily_var = Decimal("1.025")  # 2.5% positive surge
                volume = 2000000  # 2.5x volume expansion
            else:
                daily_var = Decimal(str(1.0 + (((idx * 17 + 3) % 21) - 10) * 0.003))
                volume = 500000 + ((idx * 131) % 400000)

            close_p = round(curr_price * daily_var, 2)
            high_p = round(close_p * Decimal("1.012"), 2)
            low_p = round(close_p * Decimal("0.988"), 2)
            open_p = round((high_p + low_p) / Decimal("2.0"), 2)

            m_bar = MarketBar(
                instrument_id=inst.id,
                trading_date=t_date,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=volume,
                source="SYNTHETIC_FIXTURE",
                retrieved_at=now_utc,
                is_adjusted=False,
                adjustment_factor=Decimal("1.000000"),
            )
            batch.append(m_bar)
            curr_price = close_p * (Decimal("1.0") + drift)

            if len(batch) >= 1000:
                session.bulk_save_objects(batch)
                session.flush()
                bars_added += len(batch)
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.flush()
            bars_added += len(batch)

    session.commit()
    session.close()
    logger.info(f"Database seeding complete! Total bars added: {bars_added}, Corporate actions added: {ca_added}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a SYNTHETIC market data fixture. This is FAKE data."
    )
    parser.add_argument(
        "--i-understand-this-is-fake",
        action="store_true",
        help="Required. Acknowledges that this script fabricates prices and that the "
        "resulting database MUST NOT be used for research.",
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Target SQLite path. MUST contain 'synthetic' or 'fixture' in the filename.",
    )
    args = parser.parse_args()

    if not args.i_understand_this_is_fake:
        raise SystemExit(
            "REFUSED: this script fabricates prices and does not fetch market data.\n"
            "Two research cycles were invalidated by exactly this confusion.\n"
            "For real NSE data use:  python -m tradecraft data backfill\n"
            "To generate a test fixture anyway, pass --i-understand-this-is-fake."
        )

    name = os.path.basename(args.db_path).lower()
    if "synthetic" not in name and "fixture" not in name:
        raise SystemExit(
            f"REFUSED: '{name}' is not an obviously-synthetic filename.\n"
            "Synthetic data must never share a path with a research database.\n"
            "Use something like data/synthetic_fixture.db."
        )

    logger.warning("=" * 78)
    logger.warning("GENERATING SYNTHETIC DATA — THESE PRICES ARE FABRICATED, NOT REAL")
    logger.warning("Target: %s", args.db_path)
    logger.warning("=" * 78)
    seed_database(args.db_path)


if __name__ == "__main__":
    main()
