from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from tradecraft.config import settings
from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument, MarketBar


# Try to initialize the Postgres test engine based on configuration
@pytest.fixture(scope="module")
def postgres_engine():
    db_url = settings.database_url
    # Ensure it's postgresql
    if not db_url or "postgresql" not in db_url:
        pytest.skip("PostgreSQL database URL is not configured.")

    try:
        engine = create_engine(db_url, connect_args={"connect_timeout": 2})
        # Try to connect to see if the database is actually online
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except OperationalError:
        pytest.skip("PostgreSQL database is offline or unreachable.")


@pytest.fixture(scope="module")
def db_schema(postgres_engine):
    # Setup: Create tables
    Base.metadata.create_all(bind=postgres_engine)
    yield postgres_engine
    # Teardown: Drop tables to leave database clean
    Base.metadata.drop_all(bind=postgres_engine)


@pytest.fixture
def db_session(db_schema):
    connection = db_schema.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_postgres_uniqueness_constraints(db_session):
    # 1. Test duplicate instrument (exchange + symbol uniqueness)
    inst1 = Instrument(
        symbol="TCS",
        exchange="NSE",
        isin="INE467B01029",
        name="Tata Consultancy Services Ltd",
        segment="EQ",
        tick_size=Decimal("0.05"),
        lot_size=1,
        is_active=True,
    )
    db_session.add(inst1)
    db_session.commit()

    # Try inserting duplicate
    inst2 = Instrument(
        symbol="TCS",
        exchange="NSE",
        isin="INE467B01029",
        name="Tata Consultancy Services Ltd (Duplicate)",
        segment="EQ",
        tick_size=Decimal("0.05"),
        lot_size=1,
        is_active=True,
    )
    db_session.add(inst2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_postgres_market_bar_uniqueness(db_session):
    inst = Instrument(
        symbol="INFY",
        exchange="NSE",
        isin="INE009A01021",
        name="Infosys Ltd",
        segment="EQ",
        tick_size=Decimal("0.05"),
        lot_size=1,
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()

    # Insert bar
    bar1 = MarketBar(
        instrument_id=inst.id,
        trading_date=date(2026, 6, 1),
        open=Decimal("1450.50"),
        high=Decimal("1465.00"),
        low=Decimal("1442.25"),
        close=Decimal("1458.75"),
        volume=1500000,
        source="zerodha",
        is_adjusted=False,
        retrieved_at=datetime.now(UTC),
    )
    db_session.add(bar1)
    db_session.commit()

    # Try inserting same bar (same instrument, date, and is_adjusted)
    bar2 = MarketBar(
        instrument_id=inst.id,
        trading_date=date(2026, 6, 1),
        open=Decimal("1450.50"),
        high=Decimal("1465.00"),
        low=Decimal("1442.25"),
        close=Decimal("1458.75"),
        volume=1500000,
        source="zerodha",
        is_adjusted=False,
        retrieved_at=datetime.now(UTC),
    )
    db_session.add(bar2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_postgres_financial_precision(db_session):
    inst = Instrument(
        symbol="NIFTY_PRECISION",
        exchange="NSE",
        isin="INE000000000",
        name="Precision Test",
        segment="EQ",
        tick_size=Decimal("0.05"),
        lot_size=1,
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()

    # Large precise fractional numbers to verify Numeric field type behavior
    precise_open = Decimal("31415.9265")
    precise_high = Decimal("31420.1234")
    precise_low = Decimal("31410.5678")
    precise_close = Decimal("31418.8888")

    bar = MarketBar(
        instrument_id=inst.id,
        trading_date=date(2026, 6, 1),
        open=precise_open,
        high=precise_high,
        low=precise_low,
        close=precise_close,
        volume=1234567,
        source="test",
        is_adjusted=False,
        retrieved_at=datetime.now(UTC),
    )
    db_session.add(bar)
    db_session.commit()

    # Retrieve and assert exact decimal precision (not float approximation)
    stmt = select(MarketBar).where(MarketBar.instrument_id == inst.id)
    retrieved = db_session.scalars(stmt).one()

    assert retrieved.open == precise_open
    assert retrieved.high == precise_high
    assert retrieved.low == precise_low
    assert retrieved.close == precise_close


def test_postgres_timezone_handling(db_session):
    inst = Instrument(
        symbol="TZ_TEST",
        exchange="NSE",
        isin="INE111111111",
        name="Timezone Test",
        segment="EQ",
        tick_size=Decimal("0.05"),
        lot_size=1,
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()

    utc_now = datetime(2026, 6, 1, 10, 30, 0, tzinfo=UTC)

    bar = MarketBar(
        instrument_id=inst.id,
        trading_date=date(2026, 6, 1),
        open=Decimal("100.00"),
        high=Decimal("100.00"),
        low=Decimal("100.00"),
        close=Decimal("100.00"),
        volume=100,
        source="test",
        is_adjusted=False,
        retrieved_at=utc_now,
    )
    db_session.add(bar)
    db_session.commit()

    # Retrieve and check
    stmt = select(MarketBar).where(MarketBar.instrument_id == inst.id)
    retrieved = db_session.scalars(stmt).one()

    # Retrieved datetime must be timezone-aware and match input UTC exactly
    assert retrieved.retrieved_at.tzinfo is not None
    # We convert retrieved time to UTC to do a direct comparison
    assert retrieved.retrieved_at.astimezone(UTC) == utc_now
