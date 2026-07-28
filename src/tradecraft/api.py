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
