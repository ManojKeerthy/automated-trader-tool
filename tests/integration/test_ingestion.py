from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.market_data.ingestion import DataIngestionWorkflow
from tradecraft.market_data.provider import TestCorporateActionsProvider, TestMarketDataProvider


@pytest.fixture
def db_session():
    # Use SQLite in-memory database for quick isolated testing
    engine = create_engine("sqlite:///:memory:")
    # SQLite does not enforce foreign keys by default, let's enable it
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_cls = sessionmaker(bind=engine)
    session = session_cls()
    yield session
    session.close()


def test_sync_instruments(db_session):
    calendar = TradingCalendar()
    # Mock data providers
    market_prov = TestMarketDataProvider(mock_bars=[], mock_instruments=[])
    corp_prov = TestCorporateActionsProvider(mock_actions=[])

    workflow = DataIngestionWorkflow(db_session, calendar, market_prov, corp_prov)

    # Run Nifty 50 sync
    workflow._sync_instruments(force_refresh=False)

    # Query database
    instruments = db_session.query(Instrument).all()
    # Should have Nifty 50 records loaded
    assert len(instruments) == 50
    assert any(inst.symbol == "RELIANCE" for inst in instruments)
    assert any(inst.symbol == "TCS" for inst in instruments)


def test_incremental_ingestion(db_session):
    calendar = TradingCalendar()

    # Setup instruments first
    inst = Instrument(symbol="RELIANCE", exchange="NSE", name="Reliance Industries", is_active=True)
    db_session.add(inst)
    db_session.commit()

    # Setup mock data provider with bars within the last 5 days
    today = date.today()
    latest_session = today
    if not calendar.is_trading_day(latest_session):
        latest_session = calendar.previous_trading_day(latest_session)

    t1 = latest_session - timedelta(days=5)
    t2 = latest_session - timedelta(days=4)

    mock_bars = [
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "trading_date": t1,
            "open": Decimal("2000"),
            "high": Decimal("2050"),
            "low": Decimal("1980"),
            "close": Decimal("2010"),
            "volume": 5000,
            "source": "mock",
            "retrieved_at": datetime.utcnow(),
        },
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "trading_date": t2,
            "open": Decimal("2010"),
            "high": Decimal("2060"),
            "low": Decimal("1990"),
            "close": Decimal("2020"),
            "volume": 6000,
            "source": "mock",
            "retrieved_at": datetime.utcnow(),
        },
    ]
    market_prov = TestMarketDataProvider(mock_bars, [])
    corp_prov = TestCorporateActionsProvider([])

    workflow = DataIngestionWorkflow(db_session, calendar, market_prov, corp_prov)

    # Run update
    report = workflow.run_update()
    assert report["failed"] == 0
    assert report["bars_inserted"] == 2

    # Run update again — should be incremental and insert 0 new bars
    report_empty = workflow.run_update()
    assert report_empty["bars_inserted"] == 0
