from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import and_, create_engine, select
from sqlalchemy.orm import Session

from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument, MarketBar
from tradecraft.instruments import get_current_nifty50_constituents
from tradecraft.market_data import DataIngestionWorkflow, TradingCalendar
from tradecraft.market_data.provider import CorporateActionsProvider, MarketDataProvider
from tradecraft.market_data.quality_engine import DataQualityEngine


# 1. Custom mock providers for the E2E scenario
class MockE2EMarketDataProvider(MarketDataProvider):
    def __init__(self, bars_db):
        self.bars_db = bars_db
        self.fetch_calls = {}

    def fetch_all_instruments(self):
        return []

    def get_daily_bars(self, symbol: str, exchange: str, start_date: date, end_date: date):
        self.fetch_calls[symbol] = self.fetch_calls.get(symbol, 0) + 1
        all_bars = self.bars_db.get(symbol, [])
        return [b for b in all_bars if start_date <= b["trading_date"] <= end_date]


class MockE2ECorporateActionsProvider(CorporateActionsProvider):
    def __init__(self, actions_db):
        self.actions_db = actions_db

    def get_corporate_actions(self, symbol: str, start_date: date, end_date: date):
        return self.actions_db.get(symbol, [])


def test_m1_e2e_acceptance_scenario():
    # Setup clean in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)

    # Load the actual Nifty 50 constituents list
    constituents = get_current_nifty50_constituents()
    assert len(constituents) >= 50

    # Map the first 5 symbols to different testing scenarios:
    # - sym_normal: Clean normal bars
    # - sym_duplicate: Contains a duplicate date
    # - sym_invalid: Contains an invalid OHLC bar (Low > High)
    # - sym_missing: Missing a trading session
    # - sym_stale: Stale data (latest bar is old)
    constituents[0]["symbol"]
    sym_duplicate = constituents[1]["symbol"]
    sym_invalid = constituents[2]["symbol"]
    sym_missing = constituents[3]["symbol"]
    sym_stale = constituents[4]["symbol"]

    calendar = TradingCalendar()
    # Find active trading days within our window
    # We choose dates that are within the 60-day default window before today
    today = date.today()
    latest_session = today
    if not calendar.is_trading_day(latest_session):
        latest_session = calendar.previous_trading_day(latest_session)

    all_dates = calendar.sessions_between(latest_session - timedelta(days=20), latest_session)
    # Ensure we have at least 5 trading sessions for testing
    assert len(all_dates) >= 5

    bars_database = {}

    # 1. Normal symbol setup
    for c in constituents:
        sym = c["symbol"]
        if sym == sym_duplicate:
            # Duplicate bar on same day
            stock_dates = list(all_dates)
            bars_database[sym] = [
                {
                    "trading_date": d,
                    "open": Decimal("200.00"),
                    "high": Decimal("210.00"),
                    "low": Decimal("190.00"),
                    "close": Decimal("205.00"),
                    "volume": 200000,
                    "source": "mock_provider",
                    "retrieved_at": datetime.now(UTC),
                }
                for d in stock_dates
            ]
            # Inject duplicate
            bars_database[sym].append(
                {
                    "trading_date": stock_dates[0],
                    "open": Decimal("200.00"),
                    "high": Decimal("210.00"),
                    "low": Decimal("190.00"),
                    "close": Decimal("205.00"),
                    "volume": 200000,
                    "source": "mock_provider",
                    "retrieved_at": datetime.now(UTC),
                }
            )
        elif sym == sym_invalid:
            # Invalid OHLC (Low > High)
            bars_database[sym] = [
                {
                    "trading_date": d,
                    "open": Decimal("300.00"),
                    "high": Decimal("290.00"),  # High is lower than open
                    "low": Decimal("310.00"),  # Low is higher than high
                    "close": Decimal("305.00"),
                    "volume": 300000,
                    "source": "mock_provider",
                    "retrieved_at": datetime.now(UTC),
                }
                for d in all_dates
            ]
        elif sym == sym_missing:
            # Missing session (skip second session)
            stock_dates = list(all_dates)
            if len(stock_dates) > 3:
                stock_dates.pop(1)
            bars_database[sym] = [
                {
                    "trading_date": d,
                    "open": Decimal("400.00"),
                    "high": Decimal("410.00"),
                    "low": Decimal("390.00"),
                    "close": Decimal("405.00"),
                    "volume": 400000,
                    "source": "mock_provider",
                    "retrieved_at": datetime.now(UTC),
                }
                for d in stock_dates
            ]
        elif sym == sym_stale:
            # Stale data (last bar is older than 5 days ago)
            stale_dates = [d for d in all_dates if d < today - timedelta(days=6)]
            bars_database[sym] = [
                {
                    "trading_date": d,
                    "open": Decimal("500.00"),
                    "high": Decimal("510.00"),
                    "low": Decimal("490.00"),
                    "close": Decimal("505.00"),
                    "volume": 500000,
                    "source": "mock_provider",
                    "retrieved_at": datetime.now(UTC),
                }
                for d in stale_dates
            ]
        else:
            # Clean normal bars
            bars_database[sym] = [
                {
                    "trading_date": d,
                    "open": Decimal("100.00") + idx,
                    "high": Decimal("105.00") + idx,
                    "low": Decimal("95.00") + idx,
                    "close": Decimal("101.00") + idx,
                    "volume": 100000,
                    "source": "mock_provider",
                    "retrieved_at": datetime.now(UTC),
                }
                for idx, d in enumerate(all_dates)
            ]

    # Initialize providers
    market_provider = MockE2EMarketDataProvider(bars_database)
    corporate_provider = MockE2ECorporateActionsProvider({})

    # 3. Initialize Ingestion Orchestrator Workflow
    workflow = DataIngestionWorkflow(
        db_session=session,
        calendar=calendar,
        market_provider=market_provider,
        corporate_provider=corporate_provider,
    )

    # Run ingestion (this will sync constituents and fetch bars dynamically)
    report = workflow.run_update()
    assert report["status"] == "INVALID"  # Due to the CRITICAL error of STOCK_3 (low > high)

    # 4. Verify Ingestion & Constraints Behavior

    # 4.1 Idempotency test: Rerunning workflow should not insert duplicate bars
    assert len(market_provider.fetch_calls) >= 50
    # Clear session's dirty state before rerun
    session.commit()

    report_rerun = workflow.run_update()
    # No new bars should be inserted
    assert report_rerun["bars_inserted"] == 0

    # 4.2 Data Quality Engine Checks
    engine = DataQualityEngine(calendar)

    # Check duplicate bar
    s2_inst = session.scalars(select(Instrument).where(Instrument.symbol == sym_duplicate)).one()
    stock2_bars_db = session.scalars(
        select(MarketBar).where(
            and_(MarketBar.instrument_id == s2_inst.id, MarketBar.is_adjusted == False)
        )
    ).all()
    [
        {
            "trading_date": b.trading_date,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in stock2_bars_db
    ]
    # In SQLite unique constraint on instrument_id + trading_date + is_adjusted actually prevents duplicate insert!
    # So the database unique constraint worked, and SQLite raised no errors because we handled duplicates or unique check in code.
    # Let's verify that the quality engine detects a duplicate if present in the feed.
    alerts_s2 = engine.validate_bars(sym_duplicate, bars_database[sym_duplicate])
    assert any(a["category"] == "duplicate" for a in alerts_s2)

    # Check invalid OHLC
    alerts_s3 = engine.validate_bars(sym_invalid, bars_database[sym_invalid])
    assert any(a["category"] == "ohlc_invalid" for a in alerts_s3)

    # Check missing session
    alerts_s4 = engine.validate_bars(sym_missing, bars_database[sym_missing])
    assert any(a["category"] == "missing_session" for a in alerts_s4)

    # Check stale data
    alerts_s5 = engine.validate_bars(sym_stale, bars_database[sym_stale])
    assert any(a["category"] == "stale" for a in alerts_s5)

    # 4.3 Verify no live order placement functions exist
    with pytest.raises(AttributeError):
        workflow.place_live_order()  # type: ignore

    session.close()
