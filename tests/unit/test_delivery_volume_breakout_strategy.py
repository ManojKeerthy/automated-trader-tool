"""Hand-computed fixture tests for DeliveryVolumeBreakoutV1Strategy (ALPHA-017).

Verified by hand (scratchpad calculation, not reverse-engineered from the strategy's own
output) before writing this test: with the fixture below, SMA50=125.7 (uptrend holds),
Donchian high (prior 20 days)=149.5 (today's high 161 breaks out), RVOL=2.0 (>= 1.5 min),
ATR14=2.25 so stop_loss_level = 160.0 - 2.0*2.25 = 155.50.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.core.db import Base
from tradecraft.core.db_models import DeliveryPosition, Instrument, MarketBar, UniverseMembership
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.strategy.v2_strategies import DeliveryVolumeBreakoutV1Strategy

TODAY = date(2026, 6, 1)


def _price_fixture() -> list[dict[str, float]]:
    closes = [100.0 + i for i in range(50)]  # days 1-50: rising 100 -> 149
    closes.append(160.0)  # day 51 (today): clean breakout
    bars = []
    for i, c in enumerate(closes):
        if i < 50:
            bars.append({"close": c, "high": c + 0.5, "low": c - 0.5, "volume": 100000.0})
        else:
            bars.append({"close": c, "high": 161.0, "low": 155.0, "volume": 200000.0})
    return bars


def _seed(
    session: Session,
    price_bars: list[dict[str, float]],
    delivery_pcts: list[float] | None,
    delivery_includes_today: bool = True,
) -> tuple[Instrument, list[date]]:
    inst = Instrument(symbol="DVBTEST", name="Delivery Vol Breakout Test Co", exchange="NSE", is_active=True)
    session.add(inst)
    session.commit()

    session.add(
        UniverseMembership(
            instrument_id=inst.id, index_name="NIFTY_50",
            effective_from=date(2026, 1, 1), effective_to=None,
            source="test_fixture", confidence="VERIFIED",
        )
    )
    dates = [TODAY - timedelta(days=len(price_bars) - 1 - i) for i in range(len(price_bars))]
    for d, b in zip(dates, price_bars, strict=True):
        session.add(
            MarketBar(
                instrument_id=inst.id, trading_date=d,
                open=Decimal(str(b["close"])), high=Decimal(str(b["high"])),
                low=Decimal(str(b["low"])), close=Decimal(str(b["close"])),
                volume=int(b["volume"]), source="test_fixture", is_adjusted=True,
            )
        )

    if delivery_pcts is not None:
        # Delivery data aligned to the tail of `dates`. When delivery_includes_today is False,
        # the window is shifted back by one day so today itself has no delivery row at all -
        # simulating NSE's own report coverage gaps (section 9).
        end_idx = len(dates) if delivery_includes_today else len(dates) - 1
        delivery_dates = dates[end_idx - len(delivery_pcts) : end_idx]
        for d, pct in zip(delivery_dates, delivery_pcts, strict=True):
            session.add(
                DeliveryPosition(
                    instrument_id=inst.id, trading_date=d,
                    traded_qty=200000, delivery_qty=int(200000 * pct / 100),
                    delivery_pct=Decimal(str(pct)), source="test_fixture",
                )
            )

    session.commit()
    return inst, dates


def _make_portal(session: Session, inst: Instrument, dates: list[date]) -> DataPortal:
    universe = PointInTimeUniverse(session, "NIFTY_50")
    portal = DataPortal(session, universe, dates[0], dates[-1])
    portal.preload([inst.id])
    portal.set_current_date(dates[-1])
    return portal


def test_fires_when_breakout_volume_and_delivery_all_confirm() -> None:
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    price_bars = _price_fixture()
    # 20 baseline days at 40% delivery, today at 55% -> ratio 1.375 >= 1.2 min.
    delivery_pcts = [40.0] * 20 + [55.0]
    inst, dates = _seed(session, price_bars, delivery_pcts)
    portal = _make_portal(session, inst, dates)

    strategy = DeliveryVolumeBreakoutV1Strategy()
    signals = strategy.evaluate(dates[-1], portal)

    assert len(signals) == 1
    assert signals[0].instrument_id == inst.id
    assert signals[0].stop_loss_level == Decimal("155.50")
    assert signals[0].max_holding_days == 30

    session.close()


def test_suppressed_when_delivery_ratio_too_low() -> None:
    """Same valid breakout + volume setup, but today's delivery is only marginally above its
    own baseline (ratio 1.05 < 1.2 min) - must not fire despite a technically valid breakout.
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    price_bars = _price_fixture()
    delivery_pcts = [40.0] * 20 + [42.0]  # ratio 1.05
    inst, dates = _seed(session, price_bars, delivery_pcts)
    portal = _make_portal(session, inst, dates)

    strategy = DeliveryVolumeBreakoutV1Strategy()
    signals = strategy.evaluate(dates[-1], portal)

    assert signals == []
    session.close()


def test_suppressed_when_todays_delivery_row_is_missing() -> None:
    """NSE's delivery report has its own coverage gaps (section 9). If today's own delivery
    row simply isn't present - even with 20 valid prior baseline days - the signal must not
    fire; missing data is excluded, never treated as passing.
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    price_bars = _price_fixture()
    delivery_pcts = [40.0] * 20  # 20 baseline days present, but nothing for today
    inst, dates = _seed(session, price_bars, delivery_pcts, delivery_includes_today=False)
    portal = _make_portal(session, inst, dates)

    strategy = DeliveryVolumeBreakoutV1Strategy()
    signals = strategy.evaluate(dates[-1], portal)

    assert signals == []
    session.close()
