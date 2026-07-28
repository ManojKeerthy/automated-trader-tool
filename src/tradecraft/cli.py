import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from tradecraft.config import settings
from tradecraft.core import SessionLocal
from tradecraft.instruments import get_current_nifty50_constituents
from tradecraft.market_data import DataIngestionWorkflow, TradingCalendar
from tradecraft.market_data.provider import (
    CorporateActionsProvider,
    MarketDataProvider,
    NSECorporateActionsProvider,
    TestCorporateActionsProvider,
    TestMarketDataProvider,
    ZerodhaMarketDataProvider,
)
from tradecraft.market_data.session import KiteSessionManager

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tradecraft.cli")


def handle_auth(args: argparse.Namespace) -> None:
    """Handle Zerodha Kite Connect authentication CLI subcommands."""
    session_manager = KiteSessionManager()

    if args.auth_cmd == "login":
        try:
            url = session_manager.get_login_url()
            print("\n" + "=" * 80)
            print("ZERODHA KITE CONNECT LOGIN")
            print("=" * 80)
            print("1. Copy and paste this URL into your web browser:")
            print(f"\n   {url}\n")
            print("2. Login with your Zerodha credentials.")
            print("3. After successful login, you will be redirected to a callback URL.")
            print("4. Copy the 'request_token' parameter from that callback URL's address bar.")
            print("5. Run this command to complete authentication:")
            print("\n   python -m tradecraft auth token YOUR_REQUEST_TOKEN\n")
            print("Note: The access token is cached locally and valid for one day.")
            print("=" * 80 + "\n")
        except Exception as e:
            print(f"Error generating login URL: {e}")
            sys.exit(1)

    elif args.auth_cmd == "token":
        if not args.token_val:
            print("Error: Missing request token. Run: python -m tradecraft auth token <token>")
            sys.exit(1)
        try:
            _token = session_manager.generate_new_session(args.token_val)
            print("\n" + "=" * 80)
            print("AUTHENTICATION SUCCESSFUL")
            print("=" * 80)
            print("Your Zerodha Kite Connect session is now active.")
            print("You can run data updates now.")
            print("=" * 80 + "\n")
        except Exception as e:
            print(f"Authentication failed: {e}")
            sys.exit(1)


def generate_dry_run_mock_bars() -> list[dict[str, Any]]:
    """Generate realistic EOD bars for dry-run testing of Nifty 50 constituents."""
    mock_bars = []
    constituents = get_current_nifty50_constituents()

    # Generate 5 days of bars for testing
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=7)

    # We use a dummy calendar just to get dates
    cal = TradingCalendar()
    trading_dates = cal.sessions_between(start_dt, end_dt)

    base_prices = {
        "RELIANCE": Decimal("2450.00"),
        "TCS": Decimal("3850.00"),
        "HDFCBANK": Decimal("1650.00"),
        "INFY": Decimal("1420.00"),
    }

    for c in constituents:
        symbol = c["symbol"]
        base_px = base_prices.get(symbol, Decimal("500.00"))

        for idx, t_date in enumerate(trading_dates):
            # Create a slight uptrend with minor noise
            o = base_px + Decimal(str(idx * 2))
            h = o + Decimal("12.50")
            lo = o - Decimal("8.20")
            cl = o + Decimal("5.10")

            mock_bars.append(
                {
                    "symbol": symbol,
                    "exchange": "NSE",
                    "trading_date": t_date,
                    "open": o,
                    "high": h,
                    "low": lo,
                    "close": cl,
                    "volume": 1200000 + (idx * 50000),
                    "source": "mock",
                    "retrieved_at": datetime.utcnow(),
                }
            )
    return mock_bars


def handle_data(args: argparse.Namespace) -> None:
    """Handle market data update CLI subcommands."""
    db_session = SessionLocal()

    from tradecraft.core.preflight import validate_database_schema

    try:
        validate_database_schema(db_session)
    except Exception as e:
        print(f"\n[PREFLIGHT ERROR]: {e}\n")
        sys.exit(1)

    calendar = TradingCalendar()

    # Run calendar validation check
    calendar.run_calendar_validation()

    dry_run = args.dry_run

    if not dry_run:
        # Check if Zerodha credentials exist
        session_manager = KiteSessionManager()
        cached_token = session_manager.get_cached_access_token()

        if not settings.KITE_API_KEY or not settings.KITE_API_SECRET:
            print("\nWARNING: Zerodha API credentials not found in env. Running in DRY-RUN mode.")
            dry_run = True
        elif not cached_token:
            print("\nERROR: No active Zerodha session. Authenticate first:")
            print("  1. Run: python -m tradecraft auth login")
            print("  2. Paste redirected callback request token:")
            print("     python -m tradecraft auth token <request_token>\n")
            sys.exit(1)

    market_provider: MarketDataProvider
    corporate_provider: CorporateActionsProvider

    if dry_run:
        logger.info("Initializing in DRY-RUN mode using TestMarketDataProvider...")
        mock_bars = generate_dry_run_mock_bars()

        # Build mock instruments list
        constituents = get_current_nifty50_constituents()
        mock_instruments = [
            {
                "symbol": c["symbol"],
                "exchange": c["exchange"],
                "isin": f"INE{idx:09d}",
                "name": c["name"],
                "segment": "EQ",
                "tick_size": Decimal("0.05"),
                "lot_size": 1,
                "instrument_token": 1000 + idx,
                "is_active": True,
            }
            for idx, c in enumerate(constituents)
        ]

        market_provider = TestMarketDataProvider(mock_bars, mock_instruments)
        # Create some mock corporate actions for testing
        mock_actions = [
            {
                "symbol": "RELIANCE",
                "action_type": "DIVIDEND",
                "ex_date": date.today() - timedelta(days=2),
                "amount": Decimal("10.00"),
                "source": "mock_exchange",
                "verified": True,
            }
        ]
        corporate_provider = TestCorporateActionsProvider(mock_actions)
    else:
        logger.info("Initializing in REAL_DATA mode using ZerodhaMarketDataProvider...")
        assert settings.KITE_API_KEY is not None
        assert cached_token is not None
        market_provider = ZerodhaMarketDataProvider(settings.KITE_API_KEY, cached_token)
        corporate_provider = NSECorporateActionsProvider()

    workflow = DataIngestionWorkflow(
        db_session=db_session,
        calendar=calendar,
        market_provider=market_provider,
        corporate_provider=corporate_provider,
    )

    try:
        print("\n" + "=" * 80)
        print("RUNNING MARKET DATA UPDATE")
        print("=" * 80)

        report = workflow.run_update(force_refresh_instruments=args.force_instruments)

        print("\nUPDATE COMPLETE REPORT:")
        print(f"Expected Latest Session: {report['latest_session']}")
        print(f"Total Nifty 50 constituents: {report['total_instruments']}")
        print(f"Processed Successfully: {report['processed_successfully']}")
        print(f"Already Current: {report['already_current']}")
        print(f"Updated With New Data: {report['updated_with_new_data']}")
        print(f"Failed Ingestions: {report['failed']}")
        print(f"Bars Inserted: {report['bars_inserted']}")
        print(f"Corporate Actions Ingested: {report['corporate_actions_found']}")

        errors_count = sum(1 for a in report["alerts"] if a["level"] == "ERROR")
        crit_count = sum(1 for a in report["alerts"] if a["level"] == "CRITICAL")
        warn_count = sum(1 for a in report["alerts"] if a["level"] == "WARNING")

        print("Data Quality Alerts:")
        print(f"  Critical: {crit_count}")
        print(f"  Errors: {errors_count}")
        print(f"  Warnings: {warn_count}")

        print(f"DATA STATUS: {report['status']}")

        if report["alerts"] and args.verbose:
            print("\nAlert details:")
            for a in report["alerts"][:20]:  # Show top 20
                print(
                    f"  [{a['level']}] {a['symbol']} - {a['category']}: {a['message']} ({a['trading_date']})"
                )

        print("=" * 80 + "\n")

    except Exception as e:
        logger.exception("Data update command failed")
        print(f"\nUpdate failed with error: {e}\n")
        sys.exit(1)
    finally:
        db_session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="TradeCraft Platform CLI Interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Auth commands
    auth_parser = subparsers.add_parser("auth", help="Manage Zerodha authentication")
    auth_sub = auth_parser.add_subparsers(dest="auth_cmd", required=True)
    auth_sub.add_parser("login", help="Generate Zerodha Kite Connect login URL")
    token_parser = auth_sub.add_parser(
        "token", help="Exchange request token for cached access token"
    )
    token_parser.add_argument(
        "token_val", type=str, help="The request_token from Zerodha redirect URL"
    )

    # Data commands
    data_parser = subparsers.add_parser("data", help="Manage market and reference data")
    data_sub = data_parser.add_subparsers(dest="data_cmd", required=True)
    update_parser = data_sub.add_parser("update", help="Run daily market data updates")
    update_parser.add_argument(
        "--force-instruments",
        action="store_true",
        help="Force refresh instrument tokens master list",
    )
    update_parser.add_argument(
        "--dry-run", action="store_true", help="Run with mock data, skipping Zerodha API calls"
    )
    update_parser.add_argument(
        "--verbose", action="store_true", help="Print detailed quality warnings/alerts"
    )

    args = parser.parse_args()

    if args.command == "auth":
        handle_auth(args)
    elif args.command == "data" and args.data_cmd == "update":
        handle_data(args)


if __name__ == "__main__":
    main()
