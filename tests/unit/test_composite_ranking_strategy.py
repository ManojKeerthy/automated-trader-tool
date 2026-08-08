"""Hand-computed fixture test for CompositeRankingV1Strategy (PROJECT_STATUS.md section 12).

Four instruments, distinct momentum and delivery-ratio values chosen so the composite score
ranking is unambiguous and verified by hand before writing this test (no ties, worked out on
paper first, not reverse-engineered from the strategy's own output):

  Momentum (63-session return):  D (5%) < B (10%) < A (50%) < C (100%)
  Delivery ratio (today/20d avg): D (0.875) < A (1.0) < C (1.5) < B (2.0)
  Percentile ranks (4 candidates, 0/(1/3)/(2/3)/1):
    A: momentum=2/3, delivery=1/3 -> composite = 0.5*(2/3+1/3) = 0.500
    B: momentum=1/3, delivery=1   -> composite = 0.5*(1/3+1)   = 0.667
    C: momentum=1,   delivery=2/3 -> composite = 0.5*(1+2/3)   = 0.833  <- highest
    D: momentum=0,   delivery=0   -> composite = 0.000

With top_percentile_cutoff=0.25 and 4 candidates, top_count=1 -> only C should be selected,
despite C not having the single highest delivery ratio (B does) - the point of a *composite*
score is exactly that neither signal alone determines the outcome.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.core.db import Base
from tradecraft.core.db_models import DeliveryPosition, Instrument, MarketBar, UniverseMembership
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.strategy.v2_strategies import CompositeRankingV1Strategy, _percentile_ranks

TODAY = date(2026, 6, 1)
N_BARS = 80  # >= max(momentum_lookback=63, trend_ma=50) + margin


def test_percentile_ranks_hand_computed() -> None:
    ranks = _percentile_ranks([30.0, 10.0, 20.0])
    assert ranks == [1.0, 0.0, 0.5]


def _price_series(start: float, end: float) -> list[float]:
    """Linear rise start -> end over N_BARS sessions (always monotonic, so Close > SMA50
    holds automatically for every instrument built this way).
    """
    return [start + i * (end - start) / (N_BARS - 1) for i in range(N_BARS)]


def _seed_instrument(
    session: Session, symbol: str, start: float, end: float, delivery_today: float
) -> Instrument:
    inst = Instrument(symbol=symbol, name=f"{symbol} Co", exchange="NSE", is_active=True)
    session.add(inst)
    session.commit()

    session.add(
        UniverseMembership(
            instrument_id=inst.id, index_name="NIFTY_50",
            effective_from=date(2026, 1, 1), effective_to=None,
            source="test_fixture", confidence="VERIFIED",
        )
    )
    closes = _price_series(start, end)
    dates = [TODAY - timedelta(days=N_BARS - 1 - i) for i in range(N_BARS)]
    for d, c in zip(dates, closes, strict=True):
        session.add(
            MarketBar(
                instrument_id=inst.id, trading_date=d,
                open=Decimal(str(round(c, 4))), high=Decimal(str(round(c + 0.5, 4))),
                low=Decimal(str(round(c - 0.5, 4))), close=Decimal(str(round(c, 4))),
                volume=100000, source="test_fixture", is_adjusted=True,
            )
        )

    # Delivery: 20 baseline days at 40.0%, today at `delivery_today`.
    delivery_dates = dates[-21:]
    delivery_pcts = [40.0] * 20 + [delivery_today]
    for d, pct in zip(delivery_dates, delivery_pcts, strict=True):
        session.add(
            DeliveryPosition(
                instrument_id=inst.id, trading_date=d,
                traded_qty=200000, delivery_qty=int(200000 * pct / 100),
                delivery_pct=Decimal(str(pct)), source="test_fixture",
            )
        )

    session.commit()
    return inst


def test_composite_score_selects_neither_pure_momentum_nor_pure_delivery_winner() -> None:
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    # delivery baseline is 40.0 for all; delivery_today set so ratio = delivery_today/40.
    inst_a = _seed_instrument(session, "INSTA", 100.0, 150.0, delivery_today=40.0)   # mom 50%,  ratio 1.0
    inst_b = _seed_instrument(session, "INSTB", 100.0, 110.0, delivery_today=80.0)   # mom 10%,  ratio 2.0 (best delivery)
    inst_c = _seed_instrument(session, "INSTC", 100.0, 200.0, delivery_today=60.0)   # mom 100%, ratio 1.5 (best composite)
    inst_d = _seed_instrument(session, "INSTD", 100.0, 105.0, delivery_today=35.0)   # mom 5%,   ratio 0.875

    universe = PointInTimeUniverse(session, "NIFTY_50")
    portal = DataPortal(session, universe, TODAY - timedelta(days=N_BARS + 10), TODAY)
    portal.preload([inst_a.id, inst_b.id, inst_c.id, inst_d.id])
    portal.set_current_date(TODAY)

    strategy = CompositeRankingV1Strategy()
    signals = strategy.evaluate(TODAY, portal)

    assert len(signals) == 1
    assert signals[0].instrument_id == inst_c.id  # highest composite, not highest of either alone

    session.close()
