import logging
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from tradecraft.core import get_db
from tradecraft.core.db_models import CorporateAction, Instrument, MarketBar
from tradecraft.market_data import TradingCalendar
from tradecraft.market_data.quality_engine import DataQualityEngine
from tradecraft.market_data.session import KiteSessionManager

logger = logging.getLogger("tradecraft.api")

app = FastAPI(
    title="TradeCraft API",
    description="Backend API for the Autonomous Indian Swing Trading Platform",
    version="0.1.0",
)


@app.get("/api/instruments", response_model=list[dict[str, Any]])
def get_instruments(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Fetch the list of all master instruments."""
    stmt = select(Instrument)
    instruments = db.scalars(stmt).all()
    return [
        {
            "id": str(i.id),
            "symbol": i.symbol,
            "exchange": i.exchange,
            "isin": i.isin,
            "name": i.name,
            "segment": i.segment,
            "tick_size": float(i.tick_size),
            "lot_size": i.lot_size,
            "is_active": i.is_active,
            "instrument_token": i.instrument_token,
        }
        for i in instruments
    ]


@app.get("/api/universe/nifty50", response_model=list[dict[str, Any]])
def get_universe_nifty50(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Fetch the current Nifty 50 constituents master list."""
    stmt = select(Instrument).where(Instrument.is_active == True)
    instruments = db.scalars(stmt).all()
    return [
        {
            "symbol": i.symbol,
            "name": i.name,
            "isin": i.isin,
            "exchange": i.exchange,
            "nifty50_member_from": i.nifty50_member_from.isoformat()
            if i.nifty50_member_from
            else None,
        }
        for i in instruments
    ]


@app.get("/api/bars", response_model=list[dict[str, Any]])
def get_bars(
    symbol: str = Query(..., description="NSE Stock Symbol"),
    start: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Fetch daily price bars (OHLCV) for a symbol."""
    stmt = select(Instrument).where(and_(Instrument.symbol == symbol, Instrument.exchange == "NSE"))
    inst = db.scalars(stmt).first()
    if not inst:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found.")

    query = select(MarketBar).where(
        and_(MarketBar.instrument_id == inst.id, MarketBar.is_adjusted == False)
    )

    if start:
        query = query.where(MarketBar.trading_date >= date.fromisoformat(start))
    if end:
        query = query.where(MarketBar.trading_date <= date.fromisoformat(end))

    query = query.order_by(MarketBar.trading_date.asc())
    bars = db.scalars(query).all()

    return [
        {
            "date": b.trading_date.isoformat(),
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": b.volume,
            "source": b.source,
        }
        for b in bars
    ]


@app.get("/api/corporate-actions", response_model=list[dict[str, Any]])
def get_corporate_actions(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Fetch all recorded corporate actions."""
    stmt = select(CorporateAction).order_by(CorporateAction.ex_date.desc())
    actions = db.scalars(stmt).all()
    return [
        {
            "symbol": a.instrument.symbol if a.instrument else None,
            "action_type": a.action_type,
            "ex_date": a.ex_date.isoformat(),
            "record_date": a.record_date.isoformat() if a.record_date else None,
            "amount": float(a.amount) if a.amount else None,
            "ratio_from": a.ratio_from,
            "ratio_to": a.ratio_to,
            "verified": a.verified,
        }
        for a in actions
    ]


@app.get("/api/data-quality", response_model=dict[str, Any])
def get_data_quality_report(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Run data quality analysis across all active instruments."""
    calendar = TradingCalendar()
    engine = DataQualityEngine(calendar)

    stmt = select(Instrument).where(Instrument.is_active == True)
    instruments = db.scalars(stmt).all()

    all_alerts = []
    instruments_status = {}
    overall_status = "READY"

    for inst in instruments:
        # Load last 30 bars
        bars_stmt = (
            select(MarketBar)
            .where(and_(MarketBar.instrument_id == inst.id, MarketBar.is_adjusted == False))
            .order_by(MarketBar.trading_date.desc())
            .limit(30)
        )
        bars = db.scalars(bars_stmt).all()
        bar_dicts = [
            {
                "trading_date": b.trading_date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in reversed(bars)
        ]

        alerts = engine.validate_bars(inst.symbol, bar_dicts)
        inst_status = "READY"

        for a in alerts:
            all_alerts.append(
                {
                    "symbol": inst.symbol,
                    "level": a["level"],
                    "category": a["category"],
                    "message": a["message"],
                    "trading_date": a["trading_date"].isoformat() if a["trading_date"] else None,
                }
            )
            if a["level"] in ("ERROR", "CRITICAL"):
                inst_status = "INVALID"
                overall_status = "INVALID"
            elif a["level"] == "WARNING" and inst_status == "READY":
                inst_status = "STALE"
                if overall_status == "READY":
                    overall_status = "STALE"

        instruments_status[inst.symbol] = inst_status

    # Get data freshness info
    latest_bar_stmt = select(MarketBar).order_by(MarketBar.retrieved_at.desc()).limit(1)
    latest_bar = db.scalars(latest_bar_stmt).first()
    last_update = latest_bar.retrieved_at.isoformat() if latest_bar else None

    return {
        "status": overall_status,
        "last_update": last_update,
        "total_alerts": len(all_alerts),
        "alerts": all_alerts,
        "instruments": instruments_status,
    }


@app.get("/api/auth/login-url")
def get_login_url() -> dict[str, str]:
    """Get Zerodha login redirect URL."""
    try:
        manager = KiteSessionManager()
        return {"url": manager.get_login_url()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/callback")
def auth_callback(
    request_token: str = Query(..., description="Zerodha callback request token"),
) -> HTMLResponse:
    """Callback landing endpoint to exchange request token."""
    try:
        manager = KiteSessionManager()
        manager.generate_new_session(request_token)
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Authentication Successful</title>
                    <style>
                        body { font-family: sans-serif; background-color: #1e1e1e; color: #f5f5f5; text-align: center; padding-top: 100px; }
                        h1 { color: #4caf50; }
                    </style>
                </head>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>Your Zerodha Kite Connect login session has been successfully cached.</p>
                    <p>You can close this window now and run the data update CLI or check the status page.</p>
                </body>
            </html>
            """,
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Dashboard html served directly
@app.get("/", response_class=HTMLResponse)
def index_dashboard() -> HTMLResponse:
    """Serve the minimal Market Data monitoring status dashboard."""
    # We will read from HTML file in the project
    html_path = Path(__file__).resolve().parent / "dashboard" / "index.html"
    if html_path.exists():
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        # Fallback inline simple dashboard
        return HTMLResponse(
            content="""
            <html>
                <head><title>TradeCraft</title></head>
                <body><h1>TradeCraft Dashboard Placeholder</h1></body>
            </html>
            """
        )


# ---------------------------------------------------------------------------
# M2 Research & Strategy Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/strategies", response_model=list[dict[str, Any]])
def list_strategies() -> list[dict[str, Any]]:
    """List available research and reference strategies."""
    return [
        {
            "id": "ref_buy_and_hold",
            "name": "Reference Buy & Hold",
            "version": "1.0.0",
            "description": "Buy and hold reference strategy (REFERENCE / TEST STRATEGY — NOT APPROVED FOR LIVE TRADING)",
        },
        {
            "id": "ref_sma_crossover",
            "name": "Reference Moving Average Crossover",
            "version": "1.0.0",
            "description": "Moving average crossover test strategy (REFERENCE / TEST STRATEGY — NOT APPROVED FOR LIVE TRADING)",
        },
    ]


@app.post("/api/backtest/run", response_model=dict[str, Any])
def run_backtest(
    strategy_id: str = Query("ref_buy_and_hold", description="Strategy ID"),
    start_date_str: str = Query("2026-01-01", description="Start date (YYYY-MM-DD)"),
    end_date_str: str = Query("2026-07-28", description="End date (YYYY-MM-DD)"),
    capital: float = Query(50000.0, description="Initial capital in INR"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run a strategy backtest and return structured results."""
    from decimal import Decimal

    from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine
    from tradecraft.strategy.base import Strategy  # noqa: TC001
    from tradecraft.strategy.reference_strategies import BuyAndHoldStrategy, SMACrossoverStrategy

    cal = TradingCalendar()

    strat: Strategy
    if strategy_id == "ref_buy_and_hold":
        strat = BuyAndHoldStrategy()
    elif strategy_id == "ref_sma_crossover":
        strat = SMACrossoverStrategy()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown strategy {strategy_id}")

    config = BacktestConfig(
        strategy=strat,
        start_date=date.fromisoformat(start_date_str),
        end_date=date.fromisoformat(end_date_str),
        initial_capital=Decimal(str(capital)),
    )

    engine = BacktestEngine(db_session=db, calendar_instance=cal)
    res = engine.run(config)

    return {
        "run_id": str(res.run_id),
        "strategy": strat.name,
        "version": strat.version,
        "research_quality": res.research_quality,
        "warnings": res.warnings,
        "metrics": res.metrics.to_dict(),
        "total_trades": len(res.trades),
        "equity_curve": [
            {
                "date": snap.trading_date.isoformat(),
                "equity": float(snap.total_equity),
                "drawdown_pct": float(snap.drawdown_pct),
            }
            for snap in res.equity_curve
        ],
    }


# ---------------------------------------------------------------------------
# M3A Screening & Regime Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/regime/current", response_model=dict[str, Any])
def get_current_regime(
    as_of: str | None = Query(None, description="Observation date (YYYY-MM-DD), default latest"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get market regime classification as of a specific date."""
    from tradecraft.screening.regime import MarketRegimeEngine, RegimeDefinition

    query_date = date.fromisoformat(as_of) if as_of else date.today()

    # Query benchmark close prices up to query_date
    stmt = (
        select(MarketBar)
        .where(and_(MarketBar.is_adjusted == False, MarketBar.trading_date <= query_date))  # noqa: E712
        .order_by(MarketBar.trading_date.asc())
    )
    bars = db.scalars(stmt).all()

    if not bars:
        return {
            "observation_date": query_date.isoformat(),
            "trend": "SIDEWAYS",
            "volatility": "NORMAL",
            "breadth": "UNAVAILABLE",
            "overall_quality": "UNAVAILABLE",
            "message": "No market bars available for regime classification",
        }

    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "date": b.trading_date,
                "close": float(b.close),
                "high": float(b.high),
                "low": float(b.low),
            }
            for b in bars
        ]
    )
    df.set_index("date", inplace=True)

    engine = MarketRegimeEngine(RegimeDefinition())
    snapshot = engine.classify(
        observation_date=query_date,
        benchmark_close=df["close"],
        benchmark_high=df["high"],
        benchmark_low=df["low"],
    )

    return {
        "observation_date": snapshot.observation_date.isoformat(),
        "regime_version": snapshot.regime_version,
        "trend": snapshot.trend,
        "volatility": snapshot.volatility,
        "breadth": snapshot.breadth,
        "trend_quality": snapshot.trend_quality,
        "volatility_quality": snapshot.volatility_quality,
        "breadth_quality": snapshot.breadth_quality,
        "overall_quality": snapshot.overall_quality,
        "metrics": snapshot.metrics,
    }


@app.post("/api/screening/run", response_model=dict[str, Any])
def run_screening(
    screen_date_str: str | None = Query(None, description="Screening date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run strategy-neutral screening on stored instruments."""
    from tradecraft.screening.eligibility import InstrumentData
    from tradecraft.screening.engine import ScreeningConfig, ScreeningEngine

    screen_date = date.fromisoformat(screen_date_str) if screen_date_str else date.today()

    # Query active instruments
    inst_stmt = select(Instrument).where(Instrument.is_active == True)  # noqa: E712
    instruments = db.scalars(inst_stmt).all()

    if not instruments:
        return {
            "screen_date": screen_date.isoformat(),
            "total_universe": 0,
            "eligible_count": 0,
            "candidate_count": 0,
            "candidates": [],
        }

    # Load bar metadata per instrument
    inst_data_list = []
    for inst in instruments:
        bars_stmt = (
            select(MarketBar)
            .where(and_(MarketBar.instrument_id == inst.id, MarketBar.is_adjusted == False))  # noqa: E712
            .order_by(MarketBar.trading_date.asc())
        )
        bars = db.scalars(bars_stmt).all()

        total_bars = len(bars)
        earliest = bars[0].trading_date if bars else None
        latest = bars[-1].trading_date if bars else None
        latest_close = float(bars[-1].close) if bars else None

        # Compute 20-day average traded value
        avg_tv = None
        avg_vol = None
        if len(bars) >= 20:
            last_20 = bars[-20:]
            avg_tv = sum(float(b.close) * b.volume for b in last_20) / 20.0
            avg_vol = sum(b.volume for b in last_20) / 20.0

        inst_data_list.append(
            InstrumentData(
                instrument_id=inst.id,
                symbol=inst.symbol,
                is_active=inst.is_active,
                total_bars=total_bars,
                earliest_date=earliest,
                latest_date=latest,
                latest_close=latest_close,
                avg_traded_value_20=avg_tv,
                avg_volume_20=avg_vol,
            )
        )

    engine = ScreeningEngine(ScreeningConfig())
    res = engine.run(screen_date=screen_date, instruments=inst_data_list)

    return {
        "screen_date": res.screen_date.isoformat(),
        "screening_version": res.screening_version,
        "eligibility_config_version": res.eligibility_config_version,
        "liquidity_config_version": res.liquidity_config_version,
        "regime_definition_version": res.regime_definition_version,
        "total_universe": res.total_universe,
        "eligible_count": res.eligible_count,
        "excluded_count": res.excluded_count,
        "candidate_count": res.candidate_count,
        "exclusion_summary": res.exclusion_summary,
        "candidates": [
            {
                "instrument_id": str(c.instrument_id),
                "symbol": c.symbol,
                "features": c.features,
                "research_quality_flags": c.research_quality_flags,
            }
            for c in res.candidates
        ],
    }


# ---------------------------------------------------------------------------
# M3B Research Laboratory Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/research/graveyard")
def get_research_graveyard(
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve all rejected strategy configurations stored in the Research Graveyard."""
    import sqlalchemy as sa

    from tradecraft.core.db_models import ResearchGraveyardModel

    entries = db.scalars(
        sa.select(ResearchGraveyardModel).order_by(ResearchGraveyardModel.created_at.desc())
    ).all()

    return [
        {
            "id": str(e.id),
            "strategy_id": e.strategy_id,
            "strategy_family": e.strategy_family,
            "strategy_version": e.strategy_version,
            "configuration_hash": e.configuration_hash,
            "parameters": e.parameters_json,
            "rejection_reason_code": e.rejection_reason_code,
            "rejection_details": e.rejection_details,
            "stage_failed": e.stage_failed,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@app.post("/api/research/lab/run")
def run_m3b_research_lab_endpoint(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Trigger the M3B Strategy Research Laboratory execution."""
    from tradecraft.market_data.calendar import TradingCalendar
    from tradecraft.research.lab import M3BResearchLaboratory

    cal = TradingCalendar()
    lab = M3BResearchLaboratory(db_session=db, calendar=cal)
    return lab.run_m3b_research_lab()

