"""Hand-computed fixture tests for ProfitCapOverlay (PROJECT_STATUS.md section 10).

Uses a minimal fake inner strategy that always emits one fixed signal, so the test isolates
the overlay's own target_level arithmetic rather than depending on any real strategy's entry
logic (already tested separately).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.core.db import Base
from tradecraft.core.db_models import Instrument, MarketBar, UniverseMembership
from tradecraft.instruments.universe import PointInTimeUniverse
from tradecraft.strategy.base import SignalIntent
from tradecraft.strategy.v2_strategies import BaseV2Strategy, ParameterOrigin, ProfitCapOverlay

TODAY = date(2026, 6, 1)


class _FixedSignalStrategy(BaseV2Strategy):
    """Always emits one BUY signal for a given instrument at a given stop, whatever the data
    actually looks like - a deliberately trivial inner strategy for isolating the overlay.
    """

    def __init__(self, instrument_id: uuid.UUID, stop_loss_level: Decimal, existing_target: Decimal | None = None):
        self._instrument_id = instrument_id
        self._stop = stop_loss_level
        self._existing_target = existing_target

    @property
    def strategy_id(self) -> str:
        return "strat_fixed_test"

    @property
    def name(self) -> str:
        return "Fixed Test Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_fixed_test"

    @property
    def hypothesis_statement(self) -> str:
        return "Test fixture, no real hypothesis."

    @property
    def revision_rationale(self) -> str:
        return "Test fixture."

    @property
    def parameters(self) -> dict:
        return {}

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return []

    @property
    def required_history(self) -> int:
        return 1

    def evaluate(self, current_date, data_portal, active_positions=None):
        return [
            SignalIntent(
                instrument_id=self._instrument_id,
                direction="BUY",
                order_type="MARKET",
                stop_loss_level=self._stop,
                target_level=self._existing_target,
                max_holding_days=10,
            )
        ]


def _seed(session: Session) -> tuple[Instrument, list[date]]:
    inst = Instrument(symbol="PCTEST", name="Profit Cap Test Co", exchange="NSE", is_active=True)
    session.add(inst)
    session.commit()
    session.add(
        UniverseMembership(
            instrument_id=inst.id, index_name="NIFTY_50",
            effective_from=date(2026, 1, 1), effective_to=None,
            source="test_fixture", confidence="VERIFIED",
        )
    )
    dates = [TODAY - timedelta(days=1), TODAY]
    for d in dates:
        session.add(
            MarketBar(
                instrument_id=inst.id, trading_date=d,
                open=Decimal("100.00"), high=Decimal("101.00"), low=Decimal("99.00"),
                close=Decimal("100.00"), volume=100000, source="test_fixture", is_adjusted=True,
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


def test_target_level_is_close_plus_risk_times_cap() -> None:
    """Close=100, stop=95 -> risk_per_share=5. Cap=5.0x -> target = 100 + 5*5 = 125."""
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    inst, dates = _seed(session)
    portal = _make_portal(session, inst, dates)

    inner = _FixedSignalStrategy(inst.id, stop_loss_level=Decimal("95.00"))
    overlay = ProfitCapOverlay(inner, max_r_multiple_cap=5.0)
    signals = overlay.evaluate(dates[-1], portal)

    assert len(signals) == 1
    assert signals[0].target_level == Decimal("125.00")
    assert signals[0].stop_loss_level == Decimal("95.00")  # stop untouched

    session.close()


def test_keeps_the_tighter_of_two_targets() -> None:
    """Inner strategy already sets its own target (110, i.e. 2R) which is tighter than the
    5R cap (125) - the overlay must not loosen an existing, more conservative target.
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    inst, dates = _seed(session)
    portal = _make_portal(session, inst, dates)

    inner = _FixedSignalStrategy(inst.id, stop_loss_level=Decimal("95.00"), existing_target=Decimal("110.00"))
    overlay = ProfitCapOverlay(inner, max_r_multiple_cap=5.0)
    signals = overlay.evaluate(dates[-1], portal)

    assert signals[0].target_level == Decimal("110.00")

    session.close()


def test_passes_through_unchanged_when_no_stop_is_set() -> None:
    """No stop_loss_level -> no risk basis to cap against -> signal passes through untouched
    rather than the overlay inventing a risk figure.
    """
    engine_db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_db)
    session = Session(bind=engine_db)

    inst, dates = _seed(session)
    portal = _make_portal(session, inst, dates)

    class _NoStopStrategy(_FixedSignalStrategy):
        def evaluate(self, current_date, data_portal, active_positions=None):
            return [
                SignalIntent(
                    instrument_id=self._instrument_id, direction="BUY", order_type="MARKET",
                    stop_loss_level=None, max_holding_days=10,
                )
            ]

    inner = _NoStopStrategy(inst.id, stop_loss_level=Decimal("95.00"))
    overlay = ProfitCapOverlay(inner, max_r_multiple_cap=5.0)
    signals = overlay.evaluate(dates[-1], portal)

    assert signals[0].target_level is None

    session.close()
