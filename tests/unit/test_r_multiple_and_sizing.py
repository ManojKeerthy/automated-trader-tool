"""Hand-computed fixture tests for defects F2, F2b, F3 and F4.

WHY THIS FILE EXISTS
====================
`expectancy_r` terminated all four Cycle 1 strategy families and was structurally incapable
of returning a positive number. It had no unit test. The rule adopted after the 2026-08-06
audit is:

    No metric may gate a decision unless a unit test proves it returns the correct value on
    a hand-computed fixture containing known winners, known losers, and a force-closed
    position.

Every expected value below is computed by hand in the docstring or comment above the
assertion, so a future regression is caught against arithmetic rather than against a
previously recorded output.

See docs/research/REPO_AUDIT_2026-08-06.md sections 2-4.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from tradecraft.backtesting.costs import CostBreakdown
from tradecraft.backtesting.metrics import MetricsEngine
from tradecraft.backtesting.trade_ledger import (
    R_STATUS_DEGENERATE,
    R_STATUS_NO_STOP,
    R_STATUS_OK,
    TradeLedger,
)
from tradecraft.research.risk_free_rate import RiskFreeRateConfig
from tradecraft.research.sizing import RiskBasedSizingCalculator
from tradecraft.strategy.base import SignalIntent

ZERO_COSTS = CostBreakdown()


def _ledger() -> TradeLedger:
    return TradeLedger(run_id=uuid.uuid4())


def _record(
    ledger: TradeLedger,
    *,
    entry: str,
    exit_: str,
    qty: int,
    stop: str | None,
    exit_reason: str,
    symbol: str = "TESTCO",
    risk_per_share: str | None = None,
):
    return ledger.record_trade(
        instrument_id=uuid.uuid4(),
        symbol=symbol,
        strategy_name="test",
        strategy_version="1.0.0",
        signal_date=date(2020, 1, 1),
        entry_date=date(2020, 1, 2),
        entry_price=Decimal(entry),
        exit_date=date(2020, 1, 20),
        exit_price=Decimal(exit_),
        quantity=qty,
        entry_costs=ZERO_COSTS,
        exit_costs=ZERO_COSTS,
        slippage_cost=Decimal("0"),
        exit_reason=exit_reason,
        stop_loss_level=Decimal(stop) if stop is not None else None,
        initial_risk_per_share=Decimal(risk_per_share) if risk_per_share else None,
    )


# =======================================================================================
# F2 - R-multiple plumbing
# =======================================================================================


class TestRMultipleArithmetic:
    def test_winner_r_multiple_is_hand_computed(self) -> None:
        """entry 100, stop 95 -> risk 5/share. 10 shares -> total risk 50.
        exit 120 -> gross 200, zero costs -> net 200. R = 200 / 50 = +4.0
        """
        t = _record(_ledger(), entry="100", exit_="120", qty=10, stop="95", exit_reason="TARGET")
        assert t.initial_risk_per_share == Decimal("5")
        assert t.r_multiple == Decimal("4")
        assert t.r_multiple_status == R_STATUS_OK

    def test_loser_stopped_out_is_minus_one_r(self) -> None:
        """entry 100, stop 95, exit exactly at stop. net = -50, total risk = 50 -> -1.0R."""
        t = _record(_ledger(), entry="100", exit_="95", qty=10, stop="95", exit_reason="STOP_LOSS")
        assert t.r_multiple == Decimal("-1")

    def test_force_closed_winner_scores_real_r_not_zero(self) -> None:
        """THE REGRESSION TEST FOR F2.

        Previously engine.py omitted stop_loss_level on the END_OF_BACKTEST path, so this
        trade recorded R = 0.0. Since no strategy emitted exits, every winner was force
        closed, so every winner scored zero while losers scored real negative R - making
        expectancy_r arithmetically incapable of being positive.

        entry 100, stop 90 -> risk 10/share, 10 shares -> 100 total risk.
        exit 150 -> net 500. R = 500 / 100 = +5.0
        """
        t = _record(
            _ledger(), entry="100", exit_="150", qty=10, stop="90", exit_reason="END_OF_BACKTEST"
        )
        assert t.r_multiple == Decimal("5"), "Force-closed winners must score a real R"
        assert t.r_multiple != Decimal("0")

    def test_missing_stop_is_excluded_not_scored_zero(self) -> None:
        """Unmeasurable must mean None (excluded), never 0.0 (counted as a neutral trade)."""
        t = _record(_ledger(), entry="100", exit_="150", qty=10, stop=None, exit_reason="SIGNAL")
        assert t.r_multiple is None
        assert t.r_multiple_status == R_STATUS_NO_STOP


class TestDegenerateRiskGuard:
    def test_gap_collapsed_denominator_is_excluded(self) -> None:
        """THE REGRESSION TEST FOR F2b.

        The stop is anchored to the signal-day close but the fill is the T+1 open. When the
        open gaps down to just above the stop, the risk distance collapses and R explodes -
        a -40R trade was observed in the Cycle 1 evidence.

        entry 100.20, stop 100.00 -> risk 0.20/share = 0.2% of price, below the 0.5% floor.
        Naively this would be net -102 / (0.20 * 10) = -51R.
        """
        t = _record(
            _ledger(),
            entry="100.20",
            exit_="89.99",
            qty=10,
            stop="100.00",
            exit_reason="STOP_LOSS",
        )
        assert t.r_multiple is None
        assert t.r_multiple_status == R_STATUS_DEGENERATE

    def test_risk_just_above_floor_is_measured(self) -> None:
        """entry 100, stop 99.40 -> risk 0.60 = 0.6% of price, above the 0.5% floor."""
        t = _record(
            _ledger(), entry="100", exit_="99.40", qty=10, stop="99.40", exit_reason="STOP_LOSS"
        )
        assert t.r_multiple_status == R_STATUS_OK
        assert t.r_multiple == Decimal("-1")

    def test_trailed_stop_does_not_corrupt_denominator(self) -> None:
        """R is defined by the risk taken at ENTRY, not by a stop trailed up later.

        entry 100, initial stop 90 -> risk 10/share. Caller passes an explicit entry-time
        risk of 10 even though the stop level recorded has been trailed to 110.
        exit 130 -> net 300 on 10 shares, total risk 100 -> +3.0R.
        """
        t = _record(
            _ledger(),
            entry="100",
            exit_="130",
            qty=10,
            stop="110",
            risk_per_share="10",
            exit_reason="TRAILING_STOP",
        )
        assert t.initial_risk_per_share == Decimal("10")
        assert t.r_multiple == Decimal("3")


# =======================================================================================
# Expectancy over a full hand-computed ledger
# =======================================================================================


class TestExpectancyR:
    @staticmethod
    def _mixed_ledger() -> TradeLedger:
        """Three trades, all with risk 10/share on 10 shares -> 100 total risk each.

        winner   entry 100 exit 150 -> net  500 -> +5.0R
        loser    entry 100 exit  90 -> net -100 -> -1.0R
        forced   entry 100 exit 120 -> net  200 -> +2.0R   (END_OF_BACKTEST)

        mean R = (5 - 1 + 2) / 3 = 2.0
        """
        led = _ledger()
        _record(led, entry="100", exit_="150", qty=10, stop="90", exit_reason="PROFIT_TARGET")
        _record(led, entry="100", exit_="90", qty=10, stop="90", exit_reason="STOP_LOSS")
        _record(led, entry="100", exit_="120", qty=10, stop="90", exit_reason="END_OF_BACKTEST")
        return led

    def test_expectancy_r_is_positive_for_a_profitable_ledger(self) -> None:
        led = self._mixed_ledger()
        m = MetricsEngine(RiskFreeRateConfig()).calculate(
            equity_curve=[],
            trades=led.trades,
            initial_capital=Decimal("100000"),
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        exp_r = m.metrics["expectancy_r"]
        assert exp_r.value == Decimal("2"), f"expected +2.0R, got {exp_r.value}"
        assert exp_r.status == "OK"

    def test_positive_pnl_cannot_produce_absurd_negative_r(self) -> None:
        """Guards the exact Cycle 1 absurdity: +20% return reported with -101.85R."""
        led = self._mixed_ledger()
        m = MetricsEngine(RiskFreeRateConfig()).calculate(
            equity_curve=[],
            trades=led.trades,
            initial_capital=Decimal("100000"),
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        net = sum(t.net_pnl for t in led.trades)
        assert net > 0
        assert m.metrics["expectancy_r"].value > 0, (
            "A ledger with positive net P&L and consistent risk must not report negative "
            "expectancy_r. This is the Cycle 1 failure mode."
        )

    def test_low_coverage_is_flagged_as_ungateable(self) -> None:
        """9 of 10 trades have no stop -> 10% coverage -> metric must not be gateable."""
        led = _ledger()
        _record(led, entry="100", exit_="90", qty=10, stop="90", exit_reason="STOP_LOSS")
        for _ in range(9):
            _record(led, entry="100", exit_="150", qty=10, stop=None, exit_reason="SIGNAL")

        m = MetricsEngine(RiskFreeRateConfig()).calculate(
            equity_curve=[],
            trades=led.trades,
            initial_capital=Decimal("100000"),
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        assert m.metrics["r_multiple_coverage_pct"].value == Decimal("10")
        assert m.metrics["expectancy_r"].status == "INSUFFICIENT_R_COVERAGE"

    def test_force_close_pct_is_reported(self) -> None:
        led = self._mixed_ledger()
        m = MetricsEngine(RiskFreeRateConfig()).calculate(
            equity_curve=[],
            trades=led.trades,
            initial_capital=Decimal("100000"),
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        # 1 of 3 trades force-closed
        assert m.metrics["force_close_pct"].value.quantize(Decimal("0.1")) == Decimal("33.3")


# =======================================================================================
# F3 - exit completeness
# =======================================================================================


class TestExitCompleteness:
    def test_signal_without_any_exit_is_rejected(self) -> None:
        """The Cycle 1 configuration: entry only, no stop, no target, no time stop."""
        with pytest.raises(ValueError, match="no exit path"):
            SignalIntent(instrument_id=uuid.uuid4(), direction="BUY", order_type="MARKET")

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"stop_loss_level": Decimal("95")},
            {"target_level": Decimal("110")},
            {"max_holding_days": 5},
        ],
    )
    def test_any_single_exit_path_is_sufficient(self, kwargs: dict) -> None:
        SignalIntent(instrument_id=uuid.uuid4(), **kwargs)

    def test_buy_and_hold_must_be_declared_explicitly(self) -> None:
        SignalIntent(instrument_id=uuid.uuid4(), intentional_buy_and_hold=True)

    def test_max_holding_days_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="max_holding_days"):
            SignalIntent(
                instrument_id=uuid.uuid4(), stop_loss_level=Decimal("95"), max_holding_days=0
            )

    def test_max_holding_days_reaches_the_order(self) -> None:
        """Regression: the value used to sit in metadata where nothing read it."""
        sig = SignalIntent(
            instrument_id=uuid.uuid4(), stop_loss_level=Decimal("95"), max_holding_days=7
        )
        assert sig.max_holding_days == 7


class TestTimeStopState:
    def test_position_reports_time_stop_when_due(self) -> None:
        from tradecraft.backtesting.portfolio import Position

        pos = Position(
            position_id=uuid.uuid4(),
            instrument_id=uuid.uuid4(),
            symbol="TESTCO",
            strategy_id="s",
            strategy_version="1",
            quantity=10,
            avg_entry_price=Decimal("100"),
            entry_date=date(2020, 1, 2),
            entry_fees=Decimal("0"),
            max_holding_days=3,
        )
        assert not pos.is_time_stop_due
        pos.bars_held = 2
        assert not pos.is_time_stop_due
        pos.bars_held = 3
        assert pos.is_time_stop_due

    def test_position_without_time_stop_never_expires(self) -> None:
        from tradecraft.backtesting.portfolio import Position

        pos = Position(
            position_id=uuid.uuid4(),
            instrument_id=uuid.uuid4(),
            symbol="TESTCO",
            strategy_id="s",
            strategy_version="1",
            quantity=10,
            avg_entry_price=Decimal("100"),
            entry_date=date(2020, 1, 2),
            entry_fees=Decimal("0"),
        )
        pos.bars_held = 5000
        assert not pos.is_time_stop_due


# =======================================================================================
# F4 - risk-based sizing
# =======================================================================================


class TestRiskBasedSizing:
    def setup_method(self) -> None:
        self.calc = RiskBasedSizingCalculator(
            risk_pct=Decimal("0.01"), max_position_pct=Decimal("0.20")
        )

    def test_quantity_is_hand_computed(self) -> None:
        """equity 1,000,000 at 1% risk -> 10,000 risk budget.
        entry 100, stop 95 -> risk 5/share -> 10,000 / 5 = 2000 shares.
        Notional 200,000 = exactly the 20% cap, so it is not reduced.
        """
        r = self.calc.calculate_quantity(
            portfolio_equity=Decimal("1000000"),
            available_cash=Decimal("1000000"),
            actual_fill_price=Decimal("100"),
            stop_loss_level=Decimal("95"),
        )
        assert r.is_valid
        assert r.quantity == 2000

    def test_equal_risk_across_different_stop_distances(self) -> None:
        """THE REGRESSION TEST FOR F4.

        Legacy sizing gave both names 10% of equity regardless of stop distance, so the
        wide-stop name risked several times more than the tight-stop name and R-multiples
        were not comparable across trades. Risk-based sizing must equalise rupee risk.

        Both stops are wider than 5% of price so the notional cap does not bind
        (see test_notional_cap_binds_before_risk_budget_on_tight_stops).

        near: entry 100 stop 94 -> risk  6/share -> floor(10,000 /  6) = 1666 -> risk 9,996
        far:  entry 100 stop 88 -> risk 12/share -> floor(10,000 / 12) =  833 -> risk 9,996
        """
        eq = Decimal("1000000")
        near = self.calc.calculate_quantity(eq, eq, Decimal("100"), Decimal("94"))
        far = self.calc.calculate_quantity(eq, eq, Decimal("100"), Decimal("88"))

        near_risk = Decimal(near.quantity) * Decimal("6")
        far_risk = Decimal(far.quantity) * Decimal("12")

        assert near.quantity == 1666
        assert far.quantity == 833
        # Equal to within one share of the wider instrument (integer share flooring).
        assert abs(near_risk - far_risk) <= Decimal("12")
        assert near_risk <= Decimal("10000") and far_risk <= Decimal("10000")

    def test_notional_cap_binds_before_risk_budget_on_tight_stops(self) -> None:
        """Documents a real and intentional limit of risk-based sizing.

        With risk_pct=1% and max_position_pct=20%, the notional cap binds whenever the stop
        is tighter than 5% of price:

            risk_budget / risk_per_share > max_notional / price
            <=> price / risk_per_share > 20
            <=> risk_per_share < 5% of price

        entry 100, stop 98 -> risk 2/share (2% of price, tighter than 5%).
        Risk budget alone implies 5000 shares = 500,000 notional, half of equity in one
        name. The 20% cap reduces this to 2000 shares, so the position risks 4,000 rather
        than the full 10,000 budget.

        This is deliberate: uncapped risk-based sizing concentrates capital in whichever
        name happens to have the tightest stop, which is how a single instrument came to
        contribute 42.9% of all P&L in the Cycle 1 evidence. Concentration is capped even
        at the cost of exact risk parity - but it means very tight stops under-risk, and
        expectancy_r should be read with that in mind.
        """
        eq = Decimal("1000000")
        tight = self.calc.calculate_quantity(eq, eq, Decimal("100"), Decimal("98"))

        assert tight.quantity == 2000, "notional cap should bind, not the risk budget"
        assert Decimal(tight.quantity) * Decimal("2") == Decimal("4000")
        assert Decimal(tight.quantity) * Decimal("100") == eq * self.calc.max_position_pct

    def test_notional_cap_binds_on_very_tight_stops(self) -> None:
        """entry 100, stop 99.5 -> risk 0.5/share -> risk budget implies 20,000 shares
        (2,000,000 notional), far above equity. The 20% cap (200,000) reduces it to 2000.
        """
        eq = Decimal("1000000")
        r = self.calc.calculate_quantity(eq, eq, Decimal("100"), Decimal("99.5"))
        assert r.quantity == 2000

    def test_no_stop_is_rejected_not_silently_fallen_back(self) -> None:
        r = self.calc.calculate_quantity(
            Decimal("1000000"), Decimal("1000000"), Decimal("100"), None
        )
        assert not r.is_valid
        assert r.rejection_reason == "NO_STOP_PROVIDED"

    def test_degenerate_stop_distance_is_rejected(self) -> None:
        """entry 100, stop 99.9 -> 0.1% risk, below the 0.5% floor."""
        r = self.calc.calculate_quantity(
            Decimal("1000000"), Decimal("1000000"), Decimal("100"), Decimal("99.9")
        )
        assert not r.is_valid
        assert r.rejection_reason == "DEGENERATE_RISK_DISTANCE"

    def test_never_exceeds_available_cash(self) -> None:
        r = self.calc.calculate_quantity(
            portfolio_equity=Decimal("1000000"),
            available_cash=Decimal("50000"),
            actual_fill_price=Decimal("100"),
            stop_loss_level=Decimal("95"),
        )
        assert r.required_cash <= Decimal("50000")
        assert r.quantity <= 500

    def test_no_fractional_shares(self) -> None:
        r = self.calc.calculate_quantity(
            Decimal("1000000"), Decimal("1000000"), Decimal("333.33"), Decimal("300.00")
        )
        assert isinstance(r.quantity, int)

    def test_rejects_absurd_risk_pct(self) -> None:
        with pytest.raises(ValueError):
            RiskBasedSizingCalculator(risk_pct=Decimal("0.5"))
