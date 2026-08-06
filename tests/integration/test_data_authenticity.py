"""Data authenticity gate tests.

The single most important test file in this repository.

Two full research cycles were invalidated because nothing verified that the market
database contained real prices. These tests prove the gate catches that class of failure.

`test_gate_rejects_the_actual_synthetic_generator` is the regression test for the specific
defect: it reconstructs the exact price series produced by the original
`scratch/seed_real_market_bars.py` and asserts the gate blocks it.

See docs/research/REPO_AUDIT_2026-08-06.md.
"""

from __future__ import annotations

import math
import os
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tradecraft.core.db_models import Base, Instrument, MarketBar
from tradecraft.market_data.authenticity import (
    DataAuthenticityError,
    DataAuthenticityGate,
    verify_data_authenticity,
)

TRADING_DAYS_PER_YEAR = 252


# ---------------------------------------------------------------------------- helpers


def _sessions(start: date, n: int) -> list[date]:
    """Approximate weekday-only trading sessions."""
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)
    s = maker()
    yield s
    s.close()


def _insert(
    session: Session,
    symbol: str,
    bars: list[dict],
    source: str = "ZERODHA_KITE_EOD",
) -> None:
    inst = Instrument(
        symbol=symbol,
        name=symbol,
        exchange="NSE",
        segment="EQ",
        isin=f"INE{abs(hash(symbol)) % 10**9:09d}",
        is_active=True,
    )
    session.add(inst)
    session.flush()
    session.bulk_save_objects(
        [
            MarketBar(
                instrument_id=inst.id,
                trading_date=b["date"],
                open=Decimal(str(round(b["open"], 2))),
                high=Decimal(str(round(b["high"], 2))),
                low=Decimal(str(round(b["low"], 2))),
                close=Decimal(str(round(b["close"], 2))),
                volume=int(b["volume"]),
                source=source,
                is_adjusted=True,
                adjustment_factor=Decimal("1.000000"),
            )
            for b in bars
        ]
    )
    session.flush()


# ------------------------------------------------------------------- data generators


def build_synthetic_series(base_price: float, drift: float, n: int, start: date) -> list[dict]:
    """EXACT reproduction of the original scratch/seed_real_market_bars.py logic.

    This is the series that two research cycles were run against. It must FAIL the gate.
    """
    bars: list[dict] = []
    price = base_price
    for idx, d in enumerate(_sessions(start, n)):
        is_earnings = (idx > 20) and (idx % 40 == 0)
        if is_earnings:
            daily_var = 1.025
            volume = 2_000_000
        else:
            daily_var = 1.0 + (((idx * 17 + 3) % 21) - 10) * 0.003
            volume = 500_000 + ((idx * 131) % 400_000)

        close_p = round(price * daily_var, 2)
        high_p = round(close_p * 1.012, 2)
        low_p = round(close_p * 0.988, 2)
        open_p = round((high_p + low_p) / 2.0, 2)

        bars.append(
            {
                "date": d,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            }
        )
        price = close_p * (1.0 + drift)
    return bars


def build_realistic_series(
    base_price: float,
    n: int,
    start: date,
    annual_vol: float,
    rng: random.Random,
    market: list[float],
    beta: float,
    crash_window: tuple[date, date] | None = None,
) -> list[dict]:
    """A plausible equity path: market factor + idiosyncratic noise + fat tails + a crash."""
    daily_vol = annual_vol / math.sqrt(TRADING_DAYS_PER_YEAR)
    bars: list[dict] = []
    price = base_price

    for idx, d in enumerate(_sessions(start, n)):
        idio = rng.gauss(0.0, daily_vol)
        # occasional jump (earnings / news) to create leptokurtosis
        if rng.random() < 0.012:
            idio += rng.choice([-1.0, 1.0]) * rng.uniform(0.05, 0.11)
        ret = beta * market[idx] + idio
        if crash_window and crash_window[0] <= d <= crash_window[1]:
            ret -= 0.010

        close_p = max(1.0, price * (1.0 + ret))
        # open gaps away from the previous close, independently of the close
        open_p = max(1.0, price * (1.0 + rng.gauss(0.0, daily_vol * 0.6)))
        high_p = max(open_p, close_p) * (1.0 + abs(rng.gauss(0.0, daily_vol * 0.7)))
        low_p = min(open_p, close_p) * (1.0 - abs(rng.gauss(0.0, daily_vol * 0.7)))
        volume = int(max(1000, rng.lognormvariate(math.log(1_000_000), 0.6)))

        bars.append(
            {
                "date": d,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            }
        )
        price = close_p
    return bars


def seed_realistic_universe(session: Session, n_instruments: int = 25, n_bars: int = 1600) -> None:
    """A universe that should PASS: dispersed vols, imperfect correlation, a real crash."""
    rng = random.Random(20260806)
    start = date(2016, 1, 4)
    sessions = _sessions(start, n_bars)

    # shared market factor -> realistic (not perfect) co-movement
    market = [rng.gauss(0.0003, 0.009) for _ in range(n_bars)]
    covid = (date(2020, 2, 1), date(2020, 4, 30))
    covid_idx = [i for i, d in enumerate(sessions) if covid[0] <= d <= covid[1]]
    for i in covid_idx:
        market[i] -= 0.011

    for k in range(n_instruments):
        _insert(
            session,
            f"SYM{k:03d}",
            build_realistic_series(
                base_price=rng.uniform(150, 3500),
                n=n_bars,
                start=start,
                annual_vol=rng.uniform(0.18, 0.55),  # wide dispersion
                rng=rng,
                market=market,
                beta=rng.uniform(0.6, 1.4),
                crash_window=covid,
            ),
        )
    session.flush()


# ------------------------------------------------------------------------- the tests


class TestGateRejectsSyntheticData:
    """The regression suite for the defect that invalidated Cycles 1 and 2."""

    @pytest.fixture()
    def synthetic_db(self, session: Session) -> Session:
        specs = [
            ("RELIANCE", 1200.0, 0.0004),
            ("TCS", 2000.0, 0.0003),
            ("INFY", 700.0, 0.0005),
            ("HDFCBANK", 1100.0, 0.0002),
            ("ICICIBANK", 400.0, 0.0006),
            ("TATASTEEL", 350.0, 0.0003),
            ("SBIN", 250.0, 0.0004),
            ("BHARTIARTL", 380.0, 0.0005),
            ("ITC", 240.0, 0.0002),
            ("AXISBANK", 500.0, 0.0004),
        ]
        for sym, base, drift in specs:
            _insert(
                session,
                sym,
                build_synthetic_series(base, drift, 1949, date(2016, 8, 1)),
                # the original seeder used this exact stamp - provenance strings lie
                source="ZERODHA_KITE_EOD",
            )
        session.flush()
        return session

    def test_gate_rejects_the_actual_synthetic_generator(self, synthetic_db: Session) -> None:
        """THE regression test. This exact data passed every audit in Cycles 1 and 2."""
        report = DataAuthenticityGate().run(synthetic_db)
        assert not report.passed, (
            "The gate accepted the synthetic generator output. This is the exact failure "
            "that invalidated two research cycles."
        )

    def test_honest_source_stamp_does_not_save_it(self, synthetic_db: Session) -> None:
        """Provenance is a property of the numbers, never of the source column."""
        report = DataAuthenticityGate().run(synthetic_db)
        failed = {c.name for c in report.blocking_failures}
        assert "no_synthetic_source_stamps" not in failed, (
            "Bars are stamped ZERODHA_KITE_EOD, so the source check passes - "
            "the statistical checks must be what rejects this data."
        )
        assert len(failed) >= 4

    @pytest.mark.parametrize(
        "check_name",
        [
            "cross_sectional_correlation",
            "volatility_dispersion",
            "open_differs_from_close",
            "intrabar_range_varies",
            "fat_tails_present",
            "universe_size",
        ],
    )
    def test_each_signature_defect_is_detected(
        self, synthetic_db: Session, check_name: str
    ) -> None:
        report = DataAuthenticityGate().run(synthetic_db)
        failed = {c.name for c in report.blocking_failures}
        assert check_name in failed, f"{check_name} should have failed. Failures: {sorted(failed)}"

    def test_verify_raises_with_actionable_message(self, synthetic_db: Session) -> None:
        with pytest.raises(DataAuthenticityError) as exc:
            verify_data_authenticity(synthetic_db)
        msg = str(exc.value)
        assert "DATA_AUTHENTICITY_FAILED" in msg
        assert "data backfill" in msg, "The error must tell the operator how to fix it."

    def test_report_is_serialisable(self, synthetic_db: Session) -> None:
        d = DataAuthenticityGate().run(synthetic_db).to_dict()
        assert d["passed"] is False
        assert d["instrument_count"] == 10


class TestGateAcceptsRealisticData:
    """Guards against a gate so strict that real data cannot pass it."""

    @pytest.fixture()
    def realistic_db(self, session: Session) -> Session:
        seed_realistic_universe(session)
        return session

    def test_realistic_universe_passes(self, realistic_db: Session) -> None:
        report = DataAuthenticityGate().run(realistic_db)
        assert report.passed, (
            "A realistic universe was rejected - the gate is too strict and will block "
            "legitimate research:\n" + report.render()
        )

    def test_verify_does_not_raise(self, realistic_db: Session) -> None:
        report = verify_data_authenticity(realistic_db)
        assert report.passed


class TestTargetedDefects:
    """Each check should fire on the specific defect it exists to catch."""

    def test_lockstep_universe_is_rejected(self, session: Session) -> None:
        """Identical returns across names -> cross-sectional research is vacuous."""
        rng = random.Random(7)
        start = date(2016, 1, 4)
        n = 1200
        market = [rng.gauss(0.0004, 0.011) for _ in range(n)]
        for k in range(25):
            bars = build_realistic_series(
                base_price=100.0 * (k + 1),
                n=n,
                start=start,
                annual_vol=0.30,
                rng=random.Random(7),  # identical seed -> identical idiosyncratic path
                market=market,
                beta=1.0,
            )
            _insert(session, f"LOCK{k:03d}", bars)
        session.flush()

        failed = {c.name for c in DataAuthenticityGate().run(session).blocking_failures}
        assert "cross_sectional_correlation" in failed

    def test_open_equals_close_is_rejected(self, session: Session) -> None:
        """The midpoint-open bug: no overnight gaps, so T+1 open execution is untested."""
        rng = random.Random(11)
        start = date(2016, 1, 4)
        n = 1200
        market = [rng.gauss(0.0004, 0.010) for _ in range(n)]
        for k in range(25):
            bars = build_realistic_series(
                100.0 * (k + 1), n, start, rng.uniform(0.2, 0.5), rng, market, rng.uniform(0.7, 1.3)
            )
            for b in bars:
                b["open"] = b["close"]  # inject the defect
            _insert(session, f"GAP{k:03d}", bars)
        session.flush()

        failed = {c.name for c in DataAuthenticityGate().run(session).blocking_failures}
        assert "open_differs_from_close" in failed

    def test_monotonic_volume_counter_is_rejected(self, session: Session) -> None:
        rng = random.Random(13)
        start = date(2016, 1, 4)
        n = 1200
        market = [rng.gauss(0.0004, 0.010) for _ in range(n)]
        for k in range(25):
            bars = build_realistic_series(
                100.0 * (k + 1), n, start, rng.uniform(0.2, 0.5), rng, market, rng.uniform(0.7, 1.3)
            )
            for i, b in enumerate(bars):
                b["volume"] = 500_000 + i * 131  # the original linear counter
            _insert(session, f"VOL{k:03d}", bars)
        session.flush()

        failed = {c.name for c in DataAuthenticityGate().run(session).blocking_failures}
        assert "volume_realism" in failed

    def test_explicit_fixture_stamp_is_rejected(self, session: Session) -> None:
        seed_realistic_universe(session, n_instruments=22, n_bars=1200)
        _insert(
            session,
            "FAKE001",
            build_synthetic_series(500.0, 0.0004, 1200, date(2016, 1, 4)),
            source="SYNTHETIC_FIXTURE",
        )
        session.flush()

        failed = {c.name for c in DataAuthenticityGate().run(session).blocking_failures}
        assert "no_synthetic_source_stamps" in failed

    def test_empty_database_is_rejected(self, session: Session) -> None:
        report = DataAuthenticityGate().run(session)
        assert not report.passed
        assert "database_populated" in {c.name for c in report.blocking_failures}

    def test_tiny_universe_is_rejected(self, session: Session) -> None:
        """10 instruments cannot support cross-sectional research."""
        seed_realistic_universe(session, n_instruments=8, n_bars=1200)
        failed = {c.name for c in DataAuthenticityGate().run(session).blocking_failures}
        assert "universe_size" in failed


class TestLiveDatabase:
    """Runs the gate against the real project database when present."""

    @pytest.mark.skipif(
        not os.path.exists("data/tradecraft.db"),
        reason="data/tradecraft.db not present",
    )
    def test_report_live_database_status(self) -> None:
        engine = create_engine("sqlite:///data/tradecraft.db")
        s = sessionmaker(bind=engine)()
        try:
            report = DataAuthenticityGate().run(s)
            print("\n" + report.render())
            assert report.passed, (
                "data/tradecraft.db failed the authenticity gate. Do not run research "
                "against it. Ingest real NSE data first:\n"
                "  python -m tradecraft data backfill --universe NIFTY100 --start 2015-01-01"
            )
        finally:
            s.close()
