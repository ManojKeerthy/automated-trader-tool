"""Hand-computed fixture tests for VolatilitySqueezeV1Strategy (ALPHA-018).

Per this project's standing rule that no metric may gate a decision unless a unit test
proves it correct on a hand-computed fixture (CLAUDE.md), not just "the DB backtest produced
plausible-looking numbers." The synthetic series below was designed and verified by hand
(scratchpad calculation, not reverse-engineered from the strategy's own output) to produce:
a genuine Bollinger-inside-Keltner squeeze for 20 sessions, no squeeze release before the
final bar, and exactly one qualifying release+breakout+uptrend bar with a known stop price.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument, MarketBar, UniverseMembership
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.strategy.v2_strategies import VolatilitySqueezeV1Strategy


def _build_bars() -> list[dict[str, float]]:
    # Bars 1-30: rising trend 100 -> 129 (step +1/day) establishes Close > SMA50 later.
    bars = [{"close": 100.0 + i, "high": 100.0 + i + 0.5, "low": 100.0 + i - 0.5} for i in range(30)]

    # Bars 31-50 (20 sessions, matching bb_period=kc_period=20): tight, nearly-flat closes
    # (small std -> narrow Bollinger Bands) with a moderate constant true range (-> wider,
    # roughly stable Keltner Channel) -> genuine squeeze (BB inside KC) throughout.
    flat_pattern = [
        0.0, 0.1, -0.1, 0.15, -0.05, 0.05, -0.15, 0.1, 0.0, -0.1,
        0.05, -0.05, 0.1, -0.1, 0.15, 0.0, -0.15, 0.05, -0.05, 0.1,
    ]
    for delta in flat_pattern:
        c = 129.5 + delta
        bars.append({"close": c, "high": c + 0.3, "low": c - 0.3})

    # Bar 51: release. Close jumps to 133 (clears the (very narrow) upper Bollinger Band),
    # with a small intraday range so the Keltron Channel doesn't widen enough to re-contain it.
    bars.append({"close": 133.0, "high": 133.6, "low": 132.4})
    return bars


def _seed(session: Session, bars: list[dict[str, float]]) -> tuple[Instrument, list[date]]:
    inst = Instrument(symbol="SQZTEST", name="Squeeze Test Co", exchange="NSE", is_active=True)
    session.add(inst)
    session.commit()

    session.add(
        UniverseMembership(
            instrument_id=inst.id,
            index_name="NIFTY_50",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            source="test_fixture",
            confidence="VERIFIED",
        )
    )
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(len(bars))]
    for d, b in zip(dates, bars, strict=True):
        session.add(
            MarketBar(
                instrument_id=inst.id,
                trading_date=d,
                open=Decimal(str(b["close"])),
                high=Decimal(str(b["high"])),
                low=Decimal(str(b["low"])),
                close=Decimal(str(b["close"])),
                volume=100000,
                source="test_fixture",
                is_adjusted=True,
            )
        )
    session.commit()
    return inst, dates


def _make_portal(session: Session, inst: Instrument, dates: list[date]) -> DataPortal:
    universe = PointInTimeUniverse(session, "NIFTY_50")
    portal = DataPortal(session, universe, dates[0], dates[-1])
    portal.preload([inst.id])
    return portal


def test_squeeze_release_fires_exactly_on_the_breakout_bar() -> None:
    """Hand-verified: squeeze holds through bar 50, releases with confirmation on bar 51.

    Independently recomputed in scratch before writing this test: bb_upper/kc_upper on bar 51
    are 131.21/131.01 (BB now wider than KC -> squeeze released), close 133.0 clears the upper
    band, Close(133.0) > SMA50(~121.16) confirms the uptrend filter. ATR14 on bar 51 is
    ~0.8429, so stop_loss_level = 133.0 - 2.0*0.8429 = 131.314 -> 131.31.
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    bars = _build_bars()
    inst, dates = _seed(session, bars)
    portal = _make_portal(session, inst, dates)
    strategy = VolatilitySqueezeV1Strategy()

    # Day 50 (last pure squeeze session, one before the release): must NOT fire.
    portal.set_current_date(dates[49])
    signals_day50 = strategy.evaluate(dates[49], portal)
    assert signals_day50 == []

    # Day 51 (the release + bullish-confirm + uptrend bar): must fire exactly once.
    portal.set_current_date(dates[50])
    signals_day51 = strategy.evaluate(dates[50], portal)
    assert len(signals_day51) == 1
    sig = signals_day51[0]
    assert sig.instrument_id == inst.id
    assert sig.direction == "BUY"
    assert sig.stop_loss_level == Decimal("131.31")
    assert sig.max_holding_days == 25

    session.close()


def test_squeeze_never_fires_mid_squeeze() -> None:
    """No day inside the 20-session squeeze window fires a signal (release is a state
    transition, not a standing condition - a strategy that fired every squeeze day rather
    than only on release would be a different, untested hypothesis).
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    bars = _build_bars()
    inst, dates = _seed(session, bars)
    portal = _make_portal(session, inst, dates)
    strategy = VolatilitySqueezeV1Strategy()

    for i in range(30, 50):  # bars 31-50, the squeeze window (0-indexed 30..49)
        portal.set_current_date(dates[i])
        signals = strategy.evaluate(dates[i], portal)
        assert signals == [], f"unexpected signal fired mid-squeeze on bar index {i}"

    session.close()
