"""Hand-computed fixture tests for VolatilitySqueezeV1RegimeFilteredStrategy's market-breadth
regime gate (PROJECT_STATUS.md section 8.5).

Reuses the exact squeeze/release fixture already verified correct in isolation
(test_vol_squeeze_strategy.py) for the "target" instrument, and adds a second "control"
instrument whose only purpose is to swing breadth above or below the 50% threshold - proving
the gate suppresses an otherwise-valid entry when the regime is OFF, and passes it through
unchanged when ON.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument, MarketBar, UniverseMembership
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.strategy.v2_strategies import VolatilitySqueezeV1RegimeFilteredStrategy

DAY51 = date(2026, 6, 1)


def _target_bars() -> list[dict[str, float]]:
    bars = [{"close": 100.0 + i, "high": 100.0 + i + 0.5, "low": 100.0 + i - 0.5} for i in range(30)]
    flat_pattern = [
        0.0, 0.1, -0.1, 0.15, -0.05, 0.05, -0.15, 0.1, 0.0, -0.1,
        0.05, -0.05, 0.1, -0.1, 0.15, 0.0, -0.15, 0.05, -0.05, 0.1,
    ]
    for delta in flat_pattern:
        c = 129.5 + delta
        bars.append({"close": c, "high": c + 0.3, "low": c - 0.3})
    bars.append({"close": 133.0, "high": 133.6, "low": 132.4})
    return bars  # 51 bars, ending on DAY51


def _control_bars(direction: str) -> list[dict[str, float]]:
    """250 bars ending on DAY51: a clean linear trend, well clear of its own 200-SMA either
    way, so this instrument's breadth contribution (above/below its SMA200) is unambiguous.
    """
    n = 250
    closes = (
        [100.0 + i for i in range(n)]  # up: 100 -> 349, close > SMA200 at the end
        if direction == "up"
        else [350.0 - i for i in range(n)]  # down: 350 -> 101, close < SMA200 at the end
    )
    return [{"close": c, "high": c + 0.5, "low": c - 0.5} for c in closes]


def _seed_instrument(session: Session, symbol: str, bars: list[dict[str, float]]) -> Instrument:
    inst = Instrument(symbol=symbol, name=f"{symbol} Co", exchange="NSE", is_active=True)
    session.add(inst)
    session.commit()

    session.add(
        UniverseMembership(
            instrument_id=inst.id,
            index_name="NIFTY_50",
            effective_from=date(2020, 1, 1),
            effective_to=None,
            source="test_fixture",
            confidence="VERIFIED",
        )
    )
    dates = [DAY51 - timedelta(days=len(bars) - 1 - i) for i in range(len(bars))]
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
    return inst


def _run(control_direction: str) -> list:
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    target = _seed_instrument(session, "SQZTEST", _target_bars())
    control = _seed_instrument(session, "CTRLTEST", _control_bars(control_direction))

    universe = PointInTimeUniverse(session, "NIFTY_50")
    portal = DataPortal(session, universe, DAY51 - timedelta(days=260), DAY51)
    portal.preload([target.id, control.id])
    portal.set_current_date(DAY51)

    strategy = VolatilitySqueezeV1RegimeFilteredStrategy()
    signals = strategy.evaluate(DAY51, portal)
    session.close()
    return signals


def test_regime_on_passes_through_a_valid_signal() -> None:
    """Control instrument in a clean uptrend -> breadth = 1/1 (target has only 51 bars, below
    the 200-bar minimum, so only control counts) = 100% >= 50% threshold -> regime ON -> the
    target's otherwise-valid squeeze release signal fires exactly as it does unfiltered.
    """
    signals = _run("up")
    assert len(signals) == 1
    assert signals[0].stop_loss_level == Decimal("131.31")


def test_regime_off_suppresses_an_otherwise_valid_signal() -> None:
    """Control instrument in a clean downtrend -> breadth = 0/1 = 0% < 50% threshold ->
    regime OFF -> the same otherwise-valid squeeze release on the target is suppressed.
    """
    signals = _run("down")
    assert signals == []
