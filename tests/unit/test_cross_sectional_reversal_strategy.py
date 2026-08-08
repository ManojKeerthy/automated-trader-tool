"""Hand-computed fixture test for CrossSectionalShortReversalV1Strategy's ranking direction
(ALPHA-019, PROJECT_STATUS.md section 8.7).

The strategy failed outright on DEVELOPMENT data (negative net_expectancy_r in aggregate and
both halves). Before trusting that as a real finding rather than an inverted-sign bug, this
proves the core mechanism does what it claims: given three instruments, all in a long-term
uptrend, with distinct 5-day returns, it selects the WORST performer (bottom decile), not the
best - and never selects an instrument that fails the uptrend filter, however bad its 5-day
return.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument, MarketBar, UniverseMembership
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.strategy.v2_strategies import CrossSectionalShortReversalV1Strategy

EVAL_DATE = date(2026, 6, 1)
N_HISTORY = 220  # trend_ma(200) + 20 margin


def _rising_then_move(final_ret_5d: float, start: float = 60.0, end: float = 100.0) -> list[float]:
    """N_HISTORY closes: a genuine 200-session rise from `start` to `end` (so SMA200 sits
    well below the current price, ~82 for these defaults), then a clean 5-day move off `end`
    ending at `final_ret_5d` (e.g. -0.15 for a -15% five-session drop). With a rising rather
    than flat base, even a sharp pullback has headroom to stay above SMA200 - a flat base was
    tried first and failed: any negative 5-day move pulled the close below its own
    near-current-price SMA200, filtering every "loser" out via the uptrend gate before ranking
    ever ran, which was a bug in the fixture, not the strategy.
    """
    warmup_n = N_HISTORY - 5
    closes = [start + i * (end - start) / (warmup_n - 1) for i in range(warmup_n)]
    for i in range(1, 6):
        closes.append(end * (1 + final_ret_5d * i / 5))
    return closes


def _seed_instrument(
    session: Session, symbol: str, closes: list[float]
) -> Instrument:
    inst = Instrument(symbol=symbol, name=f"{symbol} Co", exchange="NSE", is_active=True)
    session.add(inst)
    session.commit()

    session.add(
        UniverseMembership(
            instrument_id=inst.id, index_name="NIFTY_50",
            effective_from=date(2020, 1, 1), effective_to=None,
            source="test_fixture", confidence="VERIFIED",
        )
    )
    dates = [EVAL_DATE - timedelta(days=len(closes) - 1 - i) for i in range(len(closes))]
    for d, c in zip(dates, closes, strict=True):
        session.add(
            MarketBar(
                instrument_id=inst.id, trading_date=d,
                open=Decimal(str(c)), high=Decimal(str(c + 0.5)),
                low=Decimal(str(c - 0.5)), close=Decimal(str(c)),
                volume=100000, source="test_fixture", is_adjusted=True,
            )
        )
    session.commit()
    return inst


def test_selects_worst_5day_performer_among_uptrend_instruments() -> None:
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    # All three instruments have genuinely risen for 200 sessions (SMA200 ~82, well below the
    # ~100 pre-pullback level), so even the sharp pullback leaves them above their own SMA200.
    worst = _seed_instrument(session, "WORST", _rising_then_move(-0.15))   # -15% in 5d
    middle = _seed_instrument(session, "MIDDLE", _rising_then_move(-0.05))  # -5% in 5d
    best = _seed_instrument(session, "BEST", _rising_then_move(0.10))       # +10% in 5d

    universe = PointInTimeUniverse(session, "NIFTY_50")
    portal = DataPortal(session, universe, EVAL_DATE - timedelta(days=N_HISTORY + 10), EVAL_DATE)
    portal.preload([worst.id, middle.id, best.id])
    portal.set_current_date(EVAL_DATE)

    # bottom_percentile_cutoff=0.34 so bottom_count = max(1, int(3*0.34)) = 1 -> selects
    # exactly the single worst performer out of the three.
    strategy = CrossSectionalShortReversalV1Strategy(bottom_percentile_cutoff=0.34)
    signals = strategy.evaluate(EVAL_DATE, portal)

    assert len(signals) == 1
    assert signals[0].instrument_id == worst.id


def test_downtrend_instrument_never_selected_even_if_worst_performer() -> None:
    """A falling-knife guard check: an instrument BELOW its own SMA200 must never be
    selected, however extreme its 5-day drop - the uptrend filter is a hard gate, not a
    ranking input.
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    # Genuine long-term downtrend: base level itself has been declining for 200 sessions, so
    # even after the "recovery-ish" final close it is still below its own SMA200.
    closes = [200.0 - i * 0.6 for i in range(N_HISTORY - 5)]
    last_base = closes[-1]
    for i in range(1, 6):
        closes.append(last_base * (1 - 0.20 * i / 5))  # additional -20% over the last 5 days
    downtrend_inst = _seed_instrument(session, "DOWNTREND", closes)

    uptrend_inst = _seed_instrument(session, "MILD", _rising_then_move(-0.02))

    universe = PointInTimeUniverse(session, "NIFTY_50")
    portal = DataPortal(session, universe, EVAL_DATE - timedelta(days=N_HISTORY + 10), EVAL_DATE)
    portal.preload([downtrend_inst.id, uptrend_inst.id])
    portal.set_current_date(EVAL_DATE)

    strategy = CrossSectionalShortReversalV1Strategy(bottom_percentile_cutoff=0.6)
    signals = strategy.evaluate(EVAL_DATE, portal)

    selected_ids = {s.instrument_id for s in signals}
    assert downtrend_inst.id not in selected_ids
    assert uptrend_inst.id in selected_ids
