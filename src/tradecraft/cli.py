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


def handle_backtest(args: argparse.Namespace) -> None:
    """Handle backtest subcommands."""
    from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine
    from tradecraft.strategy.base import Strategy  # noqa: TC001
    from tradecraft.strategy.reference_strategies import BuyAndHoldStrategy, SMACrossoverStrategy

    db_session = SessionLocal()
    cal = TradingCalendar()

    if args.backtest_cmd == "run":
        # Strategy selection
        strat: Strategy | None = None
        if args.strategy == "ref_buy_and_hold":
            strat = BuyAndHoldStrategy()
        elif args.strategy == "ref_sma_crossover":
            strat = SMACrossoverStrategy(fast_period=args.fast_sma, slow_period=args.slow_sma)
        else:
            print(
                f"Error: Unknown strategy '{args.strategy}'. Run 'python -m tradecraft strategy list' to see available strategies."
            )
            sys.exit(1)

        assert strat is not None
        config = BacktestConfig(
            strategy=strat,
            start_date=date.fromisoformat(args.start),
            end_date=date.fromisoformat(args.end),
            initial_capital=Decimal(str(args.capital)),
        )

        engine = BacktestEngine(db_session=db_session, calendar_instance=cal)
        res = engine.run(config)

        print("\n" + "=" * 80)
        print("BACKTEST EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Run ID: {res.run_id}")
        print(f"Strategy: {strat.name} (v{strat.version})")
        print(f"Research Quality: {res.research_quality}")
        print(f"Period: {config.start_date} to {config.end_date}")
        print(f"Initial Capital: INR {config.initial_capital:,.2f}")

        tot_ret = res.metrics.metrics.get("total_return_pct")
        if tot_ret and tot_ret.value is not None:
            print(f"Total Return: {tot_ret.value:.2f}%")

        cagr = res.metrics.metrics.get("cagr_pct")
        if cagr and cagr.value is not None:
            print(f"CAGR: {cagr.value:.2f}%")

        sharpe = res.metrics.metrics.get("sharpe_ratio")
        if sharpe and sharpe.value is not None:
            print(f"Sharpe Ratio: {sharpe.value:.2f}")

        mdd = res.metrics.metrics.get("max_drawdown_pct")
        if mdd and mdd.value is not None:
            print(f"Max Drawdown: {mdd.value:.2f}%")

        print(f"Total Trades: {len(res.trades)}")

        if res.warnings:
            print("\nWarnings:")
            for w in res.warnings:
                print(f"  - {w}")

        print("=" * 80 + "\n")

    db_session.close()


def handle_verify(args: argparse.Namespace) -> None:
    """Run the data authenticity gate. Exit code 1 on failure so CI can enforce it."""
    import json as _json

    from tradecraft.market_data.authenticity import DataAuthenticityGate

    db_session = SessionLocal()
    try:
        report = DataAuthenticityGate().run(db_session)
        if getattr(args, "json", False):
            print(_json.dumps(report.to_dict(), indent=2))
        else:
            print(report.render())
        if not report.passed:
            sys.exit(1)
    finally:
        db_session.close()


def handle_corporate_actions(args: argparse.Namespace) -> None:
    """Detect / import / apply / list corporate actions."""
    import json as _json

    from sqlalchemy import text as _text

    db_session = SessionLocal()
    try:
        if args.ca_cmd == "detect":
            from tradecraft.corporate_actions.detector import CorporateActionDetector
            from tradecraft.corporate_actions.importer import write_template

            report = CorporateActionDetector(gap_threshold=args.threshold).run(db_session)
            if getattr(args, "json", False):
                print(_json.dumps(report.to_dict(), indent=2))
            else:
                print(report.render())

            if args.write_template:
                candidates = report.high + report.medium
                p = write_template(args.write_template, candidates)
                print(f"\n  Wrote {len(candidates)} candidate(s) to {p}")
                print("  Verify each against its NSE circular, set verified=true, then:")
                print(f"      python -m tradecraft data corporate-actions import {p}")

        elif args.ca_cmd == "import":
            from tradecraft.corporate_actions.importer import CorporateActionImporter

            res = CorporateActionImporter().load(db_session, args.csv_path)
            print(res.render())
            if not res.ok:
                sys.exit(1)

        elif args.ca_cmd == "apply":
            from tradecraft.corporate_actions.adjuster import CorporateActionAdjuster

            if args.include_unverified:
                print(
                    "\n  WARNING: applying UNVERIFIED actions. Inferred ratios are leads to\n"
                    "  check, not facts. Adjusting prices from an unverified inference\n"
                    "  replaces one silent data corruption with another.\n"
                )
            adjuster = CorporateActionAdjuster(include_unverified=args.include_unverified)
            report = adjuster.run(db_session, dry_run=not args.apply)
            print(report.render())

        elif args.ca_cmd == "list":
            rows = db_session.execute(
                _text(
                    """
                    SELECT i.symbol, ca.action_type, ca.ex_date, ca.ratio_from,
                           ca.ratio_to, ca.amount, ca.source, ca.verified
                    FROM corporate_actions ca
                    JOIN instruments i ON i.id = ca.instrument_id
                    ORDER BY i.symbol, ca.ex_date
                    """
                )
            ).all()
            if not rows:
                print("\n  No corporate actions stored.")
                print("  Start with: python -m tradecraft data corporate-actions detect\n")
                return
            print(f"\n  {len(rows)} corporate action(s):\n")
            print(f"  {'SYMBOL':<14} {'TYPE':<14} {'EX-DATE':<12} {'RATIO':<10} "
                  f"{'VERIFIED':<9} SOURCE")
            for r in rows:
                ratio = f"{r[3]}:{r[4]}" if r[3] and r[4] else (str(r[5]) if r[5] else "-")
                print(f"  {r[0]:<14} {r[1]:<14} {str(r[2]):<12} {ratio:<10} "
                      f"{str(bool(r[7])):<9} {r[6]}")
            unverified = sum(1 for r in rows if not r[7])
            if unverified:
                print(f"\n  {unverified} unverified — these are NOT applied to prices.")
    finally:
        db_session.close()


def handle_quality_report(args: argparse.Namespace) -> None:
    """Post-ingestion diagnostics. Exit code 1 when blocking defects are found."""
    import json as _json

    from tradecraft.core.db_provenance import fingerprint
    from tradecraft.market_data.quality_report import build_quality_report

    db_session = SessionLocal()
    try:
        report = build_quality_report(db_session)
        if getattr(args, "json", False):
            out = report.to_dict()
            out["provenance"] = fingerprint(db_session).to_dict()
            print(_json.dumps(out, indent=2))
        else:
            print(fingerprint(db_session).render())
            print()
            print(report.render(top_n=args.top))
        if report.blocking:
            sys.exit(1)
    finally:
        db_session.close()


def handle_purge_synthetic(args: argparse.Namespace) -> None:
    """Remove fabricated bars from the research database.

    Real bars must never be appended alongside synthetic ones: the backfill resumes from the
    earliest existing bar per instrument, so leaving fabricated rows in place would cause a
    silent real/fake mixture that is far harder to detect than the original problem.
    """
    from sqlalchemy import func, select

    from tradecraft.core.db_models import MarketBar
    from tradecraft.market_data.authenticity import DataAuthenticityGate

    db_session = SessionLocal()
    try:
        report = DataAuthenticityGate().run(db_session)
        total = db_session.scalar(select(func.count()).select_from(MarketBar)) or 0

        print("=" * 78)
        print("  PURGE SYNTHETIC MARKET DATA")
        print("=" * 78)
        print(f"  Bars currently in market_bars: {total}")
        print(f"  Authenticity gate verdict:     {'PASS' if report.passed else 'FAIL'}")

        if report.passed:
            print("\n  The database PASSES the authenticity gate. Nothing will be purged.")
            print("  If you believe it still contains fabricated data, investigate before")
            print("  deleting anything.")
            return

        print("\n  Blocking failures:")
        for c in report.blocking_failures:
            print(f"    - {c.name}: {c.observed}")

        if not args.confirm:
            print(f"\n  DRY RUN: would delete all {total} bars from market_bars.")
            print("  Re-run with --confirm to execute.")
            return

        deleted = db_session.query(MarketBar).delete()
        db_session.commit()
        print(f"\n  Deleted {deleted} bars.")
        print("\n  Next:")
        print("    python -m tradecraft data backfill --universe NIFTY100 --start 2015-01-01")
        print("    python -m tradecraft data verify")
    finally:
        db_session.close()


def handle_backfill(args: argparse.Namespace) -> None:
    """Seed the target universe and run a real historical backfill via Kite."""
    from tradecraft.instruments.universes import resolve_universe
    from tradecraft.market_data.backfill import HistoricalBackfillWorkflow

    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        target_years = max(1, (date.today() - start_date).days // 365 + 1)
    else:
        start_date = date.today() - timedelta(days=args.years * 365)
        target_years = args.years

    symbols = resolve_universe(args.universe) if not args.symbol else [args.symbol]

    print("=" * 78)
    print("  HISTORICAL BACKFILL — REAL MARKET DATA")
    print("=" * 78)
    print(f"  Universe:  {args.universe} ({len(symbols)} symbols, survivorship-reduced superset)")
    print(f"  From:      {start_date}")
    print(f"  Provider:  Zerodha Kite Connect")
    print("=" * 78)

    session_manager = KiteSessionManager()
    cached_token = session_manager.get_cached_access_token()
    if not settings.KITE_API_KEY or not cached_token:
        print("\nERROR: No active Zerodha session. Authenticate first:")
        print("  1. Run: python -m tradecraft auth login")
        print("  2. Paste redirected callback request token:")
        print("     python -m tradecraft auth token <request_token>\n")
        sys.exit(1)

    db_session = SessionLocal()
    try:
        calendar = TradingCalendar()
        provider: MarketDataProvider = ZerodhaMarketDataProvider(settings.KITE_API_KEY, cached_token)

        workflow = HistoricalBackfillWorkflow(
            db_session=db_session,
            calendar=calendar,
            market_provider=provider,
            chunk_delay_seconds=args.chunk_delay,
        )

        if not args.symbol:
            seed = workflow.seed_universe(symbols)
            print(
                f"\n  Universe seeded: {seed['created']} created, "
                f"{seed['existing']} already present, {len(seed['unresolved'])} unresolved"
            )
            if seed["unresolved"]:
                from tradecraft.instruments.universes import unresolved_symbol_guidance

                print("\n  UNRESOLVED SYMBOLS — these need mapping, not re-adding:")
                for line in unresolved_symbol_guidance(seed["unresolved"]):
                    print(f"    {line}")
                print(
                    "\n  Each is either a succession to record or a survivorship-bias hazard.\n"
                    "  Re-adding them as new symbols would create empty instruments."
                )

        report = workflow.run_backfill(
            target_years=target_years,
            instrument_symbol=args.symbol,
        )

        print(f"\n  Status:          {report['status']}")
        print(f"  Instruments:     {report['total_instruments']}")
        print(f"  Bars inserted:   {report['bars_inserted']}")
        print(f"  Chunks:          {report['chunks_processed']}")

        empty = [c for c in report["instrument_coverages"] if c.status == "EMPTY"]
        if empty:
            print(f"\n  {len(empty)} instrument(s) returned no data (delisted or bad symbol):")
            for c in empty[:20]:
                print(f"    - {c.symbol}")

        print("\n  Next: python -m tradecraft data verify")
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

    backfill_parser = data_sub.add_parser("backfill", help="Run historical market data backfill")
    backfill_parser.add_argument(
        "--years", type=int, default=2, help="Number of historical years to fetch (default: 2)"
    )
    backfill_parser.add_argument(
        "--start", type=str, help="Explicit start date YYYY-MM-DD (overrides --years)"
    )
    backfill_parser.add_argument(
        "--universe",
        type=str,
        default="NIFTY100",
        help="Index universe to seed and backfill: NIFTY50 | NIFTY100 (default: NIFTY100)",
    )
    backfill_parser.add_argument(
        "--symbol", type=str, help="Specific instrument symbol to backfill (optional)"
    )
    backfill_parser.add_argument(
        "--chunk-delay",
        type=float,
        default=0.4,
        help="Seconds to sleep between provider chunks (Kite rate limit; default: 0.4)",
    )

    # Data integrity commands
    verify_parser = data_sub.add_parser(
        "verify", help="Run the data authenticity gate against the market database"
    )
    verify_parser.add_argument(
        "--json", action="store_true", help="Emit the report as JSON instead of text"
    )

    quality_parser = data_sub.add_parser(
        "quality-report",
        help="Locate actionable defects in ingested data (unadjusted corporate actions, "
        "stale instruments, duplicate listings, coverage gaps)",
    )
    quality_parser.add_argument(
        "--json", action="store_true", help="Emit the report as JSON instead of text"
    )
    quality_parser.add_argument(
        "--top", type=int, default=25, help="Rows to show per section (default: 25)"
    )

    ca_parser = data_sub.add_parser(
        "corporate-actions", help="Detect, import and apply corporate action adjustments"
    )
    ca_sub = ca_parser.add_subparsers(dest="ca_cmd", required=True)

    ca_detect = ca_sub.add_parser(
        "detect", help="Infer candidate splits/bonuses from price discontinuities"
    )
    ca_detect.add_argument("--json", action="store_true", help="Emit JSON")
    ca_detect.add_argument(
        "--threshold", type=float, default=0.20, help="Gap size to investigate (default 0.20)"
    )
    ca_detect.add_argument(
        "--write-template",
        type=str,
        metavar="PATH",
        help="Write a CSV of candidates pre-filled for human verification",
    )

    ca_import = ca_sub.add_parser("import", help="Import human-verified actions from CSV")
    ca_import.add_argument("csv_path", type=str, help="Path to the CSV file")

    ca_apply = ca_sub.add_parser(
        "apply", help="Build the adjusted price series from verified actions"
    )
    ca_apply.add_argument(
        "--apply", action="store_true", help="Actually write. Without this it is a dry run."
    )
    ca_apply.add_argument(
        "--include-unverified",
        action="store_true",
        help="DANGEROUS: also apply unverified (inferred) actions",
    )

    ca_sub.add_parser("list", help="List corporate actions currently stored")

    purge_parser = data_sub.add_parser(
        "purge-synthetic",
        help="Delete fabricated bars so real data cannot be silently mixed with them",
    )
    purge_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Without this the command reports what it WOULD delete and exits.",
    )

    # Backtest commands
    bt_parser = subparsers.add_parser("backtest", help="Research and backtesting engine")
    bt_sub = bt_parser.add_subparsers(dest="backtest_cmd", required=True)
    bt_run = bt_sub.add_parser("run", help="Run a strategy backtest")
    bt_run.add_argument(
        "--strategy",
        type=str,
        required=True,
        help="Strategy identifier (e.g. ref_buy_and_hold, ref_sma_crossover)",
    )
    bt_run.add_argument("--start", type=str, default="2026-01-01", help="Start date (YYYY-MM-DD)")
    bt_run.add_argument("--end", type=str, default="2026-07-28", help="End date (YYYY-MM-DD)")
    bt_run.add_argument("--capital", type=float, default=50000.00, help="Initial capital in INR")
    bt_run.add_argument("--fast-sma", type=int, default=5, help="Fast SMA period")
    bt_run.add_argument("--slow-sma", type=int, default=20, help="Slow SMA period")

    # Strategy commands
    strat_parser = subparsers.add_parser("strategy", help="Strategy registry management")
    strat_sub = strat_parser.add_subparsers(dest="strat_cmd", required=True)
    strat_sub.add_parser("list", help="List registered strategies")

    args = parser.parse_args()

    if args.command == "auth":
        handle_auth(args)
    elif args.command == "data" and args.data_cmd == "update":
        handle_data(args)
    elif args.command == "data" and args.data_cmd == "backfill":
        handle_backfill(args)
    elif args.command == "data" and args.data_cmd == "verify":
        handle_verify(args)
    elif args.command == "data" and args.data_cmd == "quality-report":
        handle_quality_report(args)
    elif args.command == "data" and args.data_cmd == "corporate-actions":
        handle_corporate_actions(args)
    elif args.command == "data" and args.data_cmd == "purge-synthetic":
        handle_purge_synthetic(args)
    elif args.command == "backtest":
        handle_backtest(args)
    elif args.command == "strategy" and args.strat_cmd == "list":
        print("\nRegistered Strategies:")
        print("  - ref_buy_and_hold (v1.0.0): Reference Buy & Hold [TEST STRATEGY]")
        print(
            "  - ref_sma_crossover (v1.0.0): Reference Moving Average Crossover [TEST STRATEGY]\n"
        )


if __name__ == "__main__":
    main()
