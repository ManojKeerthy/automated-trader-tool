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
#
# CRITICAL: this module runs Base.metadata.drop_all() at both setup and teardown (see
# db_schema below), and test_alembic_migration_upgrade_path drops mid-test too. It must
# NEVER connect to the same database the real application/research pipeline uses.
# Incident 2026-08-06: this fixture used to resolve settings.database_url directly (the
# app's real DB) and silently destroyed 398K rows of ingested market data, twice in one
# session, via ordinary `pytest tests/` runs. Fixed by pointing at settings.test_database_url
# (a separate database name on the same Postgres instance) plus a hard refusal below if the
# two ever resolve to the same database.
@pytest.fixture(scope="module")
def postgres_engine():
    db_url = settings.test_database_url
    if settings.POSTGRES_HOST == "localhost":
        # Windows/Docker Desktop quirk observed 2026-08-06: "localhost" intermittently
        # resolves to ::1, and although pg_hba.conf trusts ::1/128 identically to
        # 127.0.0.1/32, connections routed through the NAT layer for ::1 sometimes fall
        # through to the scram-sha-256 catch-all rule instead, causing sporadic
        # "password authentication failed" errors under connection churn. Pinning to
        # 127.0.0.1 explicitly was 100% reliable across repeated tests; "localhost" was not.
        db_url = db_url.replace("@localhost:", "@127.0.0.1:")
    if settings.POSTGRES_TEST_DB == settings.POSTGRES_DB:
        pytest.fail(
            "POSTGRES_TEST_DB must not equal POSTGRES_DB - this test suite drops all "
            "tables in whatever database it connects to, and running it against the real "
            "research database destroys ingested market data. Refusing to proceed."
        )
    # Ensure it's postgresql
    if not db_url or "postgresql" not in db_url:
        pytest.skip("PostgreSQL test database URL is not configured.")

    try:
        engine = create_engine(db_url, connect_args={"connect_timeout": 2})
        # Try to connect to see if the database is actually online
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except OperationalError:
        pytest.skip(
            f"PostgreSQL test database '{settings.POSTGRES_TEST_DB}' is offline or "
            "unreachable. Create it with: CREATE DATABASE tradecraft_test; "
            "(as the configured Postgres user, on the same instance)."
        )


@pytest.fixture(scope="module")
def db_schema(postgres_engine):
    from alembic import command
    from alembic.config import Config

    # 1. Clean the database first (drop all tables and alembic history to make sure we are clean)
    Base.metadata.drop_all(bind=postgres_engine)
    with postgres_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

    # 2. Run migrations
    alembic_cfg = Config("alembic.ini")
    # str(url) masks the password as '***' by default in this SQLAlchemy version - that
    # silently broke Alembic's connection here until 2026-08-06 (see comment on the
    # postgres_engine fixture above). render_as_string(hide_password=False) is required.
    alembic_cfg.set_main_option(
        "sqlalchemy.url", postgres_engine.url.render_as_string(hide_password=False)
    )
    command.upgrade(alembic_cfg, "head")

    yield postgres_engine

    # Teardown: Clean the database
    Base.metadata.drop_all(bind=postgres_engine)
    with postgres_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))


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


def test_postgres_schema_parity(postgres_engine):
    from sqlalchemy import inspect

    # Check that every table and column defined in Base.metadata
    # is also present in the actual database with identical nullability and close types.
    inspector = inspect(postgres_engine)
    db_tables = inspector.get_table_names()

    for model_table in Base.metadata.tables.values():
        table_name = model_table.name
        assert table_name in db_tables, f"Table '{table_name}' is missing in the migrated database."

        db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}

        for model_col in model_table.columns:
            col_name = model_col.name
            assert col_name in db_columns, (
                f"Column '{col_name}' in table '{table_name}' is missing in the migrated database."
            )

            db_col = db_columns[col_name]
            # Verify nullability match
            assert db_col["nullable"] == model_col.nullable, (
                f"Nullability mismatch for column '{col_name}' on table '{table_name}': "
                f"DB is {db_col['nullable']}, Model is {model_col.nullable}"
            )


def test_alembic_migration_upgrade_path(postgres_engine):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    alembic_cfg = Config("alembic.ini")
    # str(url) masks the password as '***' by default in this SQLAlchemy version - that
    # silently broke Alembic's connection here until 2026-08-06 (see comment on the
    # postgres_engine fixture above). render_as_string(hide_password=False) is required.
    alembic_cfg.set_main_option(
        "sqlalchemy.url", postgres_engine.url.render_as_string(hide_password=False)
    )

    # Start clean: drop all tables and alembic history
    Base.metadata.drop_all(bind=postgres_engine)
    with postgres_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

    # 1. Upgrade to 001_initial_schema
    command.upgrade(alembic_cfg, "001_initial_schema")

    # Check that transformation_version column is NOT there yet
    inspector = inspect(postgres_engine)
    cols_001 = [col["name"] for col in inspector.get_columns("market_bars")]
    assert "transformation_version" not in cols_001

    # 2. Upgrade to 002_add_transformation_version
    command.upgrade(alembic_cfg, "002_add_transformation_version")
    inspector = inspect(postgres_engine)
    cols_002 = [col["name"] for col in inspector.get_columns("market_bars")]
    assert "transformation_version" in cols_002

    # 3. Upgrade to 003_m2_research_schema
    command.upgrade(alembic_cfg, "003_m2_research_schema")
    inspector = inspect(postgres_engine)
    assert "backtest_runs" in inspector.get_table_names()

    # 4. Upgrade to head (005_m3b_research_lab_schema)
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(postgres_engine)
    assert "feature_definitions" in inspector.get_table_names()
    assert "market_regime_snapshots" in inspector.get_table_names()
    assert "screening_runs" in inspector.get_table_names()
    assert "strategy_scorecards" in inspector.get_table_names()
    assert "walk_forward_results" in inspector.get_table_names()
    assert "research_graveyard" in inspector.get_table_names()

    # 5. Query models using a temporary session to verify queries succeed
    with Session(bind=postgres_engine) as session:
        session.scalars(select(Instrument)).all()
        session.scalars(select(MarketBar)).all()

    # Teardown: Clean the database
    Base.metadata.drop_all(bind=postgres_engine)
    with postgres_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
