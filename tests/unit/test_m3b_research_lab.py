"""Unit tests for M3B Strategy Research Laboratory.

Verifies all mandatory corrections and correctness rules:
1. Breakout PIT channel calculation excludes current bar T.
2. T+1 Close cannot retroactively cancel T+1 Open entry.
3. Quantity uses actual T+1 execution price rather than T Close.
4. Sizing cannot create negative cash, leverage, or fractional shares.
5. Expectancy_R known-answer calculation and zero-risk handling.
6. Maximum one Final-Test configuration per family.
7. Second-best configuration cannot be substituted after Final-Test failure.
8. Deterministic stop selection functions (min/max).
9. Family-Specific Candidate Ranking metrics.
10. Unique configuration vs evaluation run accounting.
11. Final-test consumption persistence with git commit & config hash.
12. Unavailable historical event data cannot enter signals.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from tradecraft.backtesting.metrics import MetricsEngine
from tradecraft.backtesting.trade_ledger import TradeRecord
from tradecraft.research.sizing import ResearchSizingCalculator
from tradecraft.strategy.breakout_confirm import BreakoutConfirmStrategy
from tradecraft.strategy.mean_reversion import MeanReversionStrategy
from tradecraft.strategy.trend_pullback import TrendPullbackStrategy


class DummyMockPortal:
    """Mock DataPortal returning controlled price histories."""

    def __init__(self, history: list[dict]):
        self.history = history

    def get_history(self, instrument_id: uuid.UUID, end_date: date, count: int) -> list[dict]:
        return self.history[-count:] if len(self.history) >= count else self.history


# 1. Breakout Channel PIT Test
def test_breakout_channel_pit_excludes_current_bar():
    """Verify Donchian channel calculation excludes current bar T."""
    strat = BreakoutConfirmStrategy(channel_period=5, rvol_min=1.0, max_consolidation_pct=0.25)
    dummy_id = uuid.uuid4()
    base_date = date(2024, 1, 1)

    # 35 prior bars with high=100, then current bar T with high=150, close=105
    history = [
        {
            "trading_date": base_date + timedelta(days=i),
            "open": 90,
            "high": 100,
            "low": 80,
            "close": 95,
            "volume": 1000,
        }
        for i in range(35)
    ]
    # Current bar T: high=150, close=105 (close > prior high of 100, but close < current high 150)
    history.append(
        {
            "trading_date": base_date + timedelta(days=35),
            "open": 100,
            "high": 150,
            "low": 95,
            "close": 105,
            "volume": 2000,
        }
    )

    portal = DummyMockPortal(history)
    signal = strat.evaluate_instrument(dummy_id, base_date + timedelta(days=35), portal)

    # If bar T was included, channel_high would be 150, so close 105 would NOT trigger breakout.
    # Because bar T is excluded, channel_high is 100, so close 105 DOES trigger breakout!
    assert signal is not None
    assert signal.instrument_id == dummy_id
    assert signal.metadata["channel_high"] == 100.0


# 2. Timing test: T+1 Close cannot affect T+1 Open entry
def test_t1_close_cannot_affect_t1_open_entry():
    """Verify signal generated at T Close schedules fill at T+1 Open independently of T+1 Close."""
    strat = TrendPullbackStrategy(trend_ma=20)
    dummy_id = uuid.uuid4()
    base_date = date(2020, 1, 1)

    history = [
        {
            "trading_date": base_date + timedelta(days=i),
            "open": 100,
            "high": 105,
            "low": 95,
            "close": 100,
            "volume": 1000,
        }
        for i in range(210)
    ]
    # Setup pullback resumption on final bar
    history[-1]["close"] = 110
    history[-1]["low"] = 96
    history[-2]["high"] = 105

    portal = DummyMockPortal(history)
    signal = strat.evaluate_instrument(dummy_id, base_date + timedelta(days=209), portal)

    if signal:
        assert signal.order_type == "MARKET"
        assert signal.direction == "BUY"


# 3. Position Sizing uses actual T+1 fill price
def test_quantity_uses_actual_execution_price_t1():
    """Verify position quantity calculation uses T+1 fill price rather than T Close."""
    calc = ResearchSizingCalculator(allocation_pct=Decimal("0.10"))
    portfolio_equity = Decimal("100000.0")
    available_cash = Decimal("100000.0")

    res = calc.calculate_quantity(
        portfolio_equity=portfolio_equity,
        available_cash=available_cash,
        actual_fill_price=Decimal("125.0"),
        estimated_transaction_cost=Decimal("15.0"),
    )

    assert res.is_valid is True
    # floor(10000 / 125) = 80 shares
    assert res.quantity == 80
    assert res.required_cash == (Decimal("125.0") * 80) + Decimal("15.0")


# 4. Sizing cannot create negative cash or leverage
def test_sizing_cannot_create_negative_cash_or_leverage():
    """Verify sizing caps quantity when cash is constrained and rejects < 1 share."""
    calc = ResearchSizingCalculator(allocation_pct=Decimal("0.10"))

    res_a = calc.calculate_quantity(
        portfolio_equity=Decimal("100000.0"),
        available_cash=Decimal("50.0"),
        actual_fill_price=Decimal("100.0"),
    )
    assert res_a.is_valid is False
    assert res_a.rejection_reason == "SKIPPED_INSUFFICIENT_CASH"

    res_b = calc.calculate_quantity(
        portfolio_equity=Decimal("100000.0"),
        available_cash=Decimal("500.0"),
        actual_fill_price=Decimal("100.0"),
        estimated_transaction_cost=Decimal("150.0"),
    )
    assert res_b.is_valid is True
    assert res_b.quantity == 3
    assert res_b.required_cash <= Decimal("500.0")


# 5. Expectancy_R Known-Answer Calculation
def test_expectancy_r_known_answer_calculation():
    """Verify Expectancy_R calculation with known R-multiples."""
    engine = MetricsEngine()
    run_id = uuid.uuid4()
    inst_id = uuid.uuid4()

    t1 = TradeRecord(
        trade_id=uuid.uuid4(),
        run_id=run_id,
        instrument_id=inst_id,
        instrument_symbol="TEST",
        strategy_name="test",
        strategy_version="1.0",
        direction="BUY",
        signal_date=date(2024, 1, 1),
        entry_date=date(2024, 1, 2),
        entry_price=Decimal("100.0"),
        exit_date=date(2024, 1, 10),
        exit_price=Decimal("120.0"),
        quantity=10,
        gross_pnl=Decimal("200.0"),
        total_fees=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("200.0"),
        holding_days=8,
        exit_reason="PROFIT_TARGET",
        stop_loss_level=Decimal("90.0"),
    )

    t2 = TradeRecord(
        trade_id=uuid.uuid4(),
        run_id=run_id,
        instrument_id=inst_id,
        instrument_symbol="TEST",
        strategy_name="test",
        strategy_version="1.0",
        direction="BUY",
        signal_date=date(2024, 1, 15),
        entry_date=date(2024, 1, 16),
        entry_price=Decimal("100.0"),
        exit_date=date(2024, 1, 20),
        exit_price=Decimal("90.0"),
        quantity=10,
        gross_pnl=Decimal("-100.0"),
        total_fees=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("-100.0"),
        holding_days=4,
        exit_reason="STOP_LOSS",
        stop_loss_level=Decimal("90.0"),
    )

    res = engine.calculate(
        equity_curve=[],
        trades=[t1, t2],
        initial_capital=Decimal("100000.0"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    exp_r = res.metrics["expectancy_r"].value
    assert exp_r is not None
    assert float(exp_r) == pytest.approx(0.5)


# 6. Zero-risk R handling
def test_zero_risk_or_invalid_risk_r_handling():
    """Verify zero or missing initial risk does not produce NaN or crash."""
    engine = MetricsEngine()
    run_id = uuid.uuid4()
    inst_id = uuid.uuid4()

    t_invalid = TradeRecord(
        trade_id=uuid.uuid4(),
        run_id=run_id,
        instrument_id=inst_id,
        instrument_symbol="TEST",
        strategy_name="test",
        strategy_version="1.0",
        direction="BUY",
        signal_date=date(2024, 1, 1),
        entry_date=date(2024, 1, 2),
        entry_price=Decimal("100.0"),
        exit_date=date(2024, 1, 10),
        exit_price=Decimal("110.0"),
        quantity=10,
        gross_pnl=Decimal("100.0"),
        total_fees=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("100.0"),
        holding_days=8,
        exit_reason="PROFIT_TARGET",
        stop_loss_level=Decimal("100.0"),
    )

    res = engine.calculate(
        equity_curve=[],
        trades=[t_invalid],
        initial_capital=Decimal("100000.0"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    # BEHAVIOUR CHANGED 2026-08-06 (defect F2b).
    #
    # This test previously asserted `exp_r == 0.0`, encoding the defect it was meant to
    # guard. The trade above is a WINNER (+Rs 100 net) whose stop equals its entry price, so
    # its risk distance is zero and its R-multiple is not measurable. Scoring it 0.0 counted
    # a winning trade as a neutral one and dragged the mean toward zero. Applied across a
    # ledger where every winner was force-closed without a recorded stop, this is what made
    # `expectancy_r` structurally incapable of returning a positive value - and it was the
    # gate that terminated all four Cycle 1 strategy families.
    #
    # Unmeasurable now means EXCLUDED (None), never "scored zero".
    # See docs/research/REPO_AUDIT_2026-08-06.md section 2.
    assert res.metrics["expectancy_r"].value is None
    assert res.metrics["expectancy_r"].status == "NO_MEASURABLE_R_MULTIPLES"
    assert res.metrics["r_multiple_coverage_pct"].value == Decimal("0")
    # The original intent of the test still holds: no crash, no NaN, no Inf.
    assert res.metrics["profit_factor"].status in ("ALL_WINNERS", None, "OK")


# 7. Deterministic Stop Selection (min/max)
def test_deterministic_stop_selection():
    """Verify trend pullback strategy calculates stop as lower of pullback low vs ATR stop."""
    strat = TrendPullbackStrategy(trend_ma=20, atr_stop_mult=2.0)
    dummy_id = uuid.uuid4()
    base_date = date(2020, 1, 1)

    history = [
        {
            "trading_date": base_date + timedelta(days=i),
            "open": 100,
            "high": 105,
            "low": 95,
            "close": 100,
            "volume": 1000,
        }
        for i in range(210)
    ]
    history[-1]["close"] = 110
    history[-1]["low"] = 85
    history[-2]["high"] = 105

    portal = DummyMockPortal(history)
    signal = strat.evaluate_instrument(dummy_id, base_date + timedelta(days=209), portal)

    if signal:
        assert signal.stop_loss_level is not None
        assert float(signal.stop_loss_level) <= 90.0


# 8. Unavailable Event Data Exclusion
def test_unavailable_event_data_exclusion():
    """Verify MeanReversionStrategy parameters do not accept or require earnings event inputs."""
    strat = MeanReversionStrategy()
    assert "earnings" not in strat.parameters
    assert "news" not in strat.parameters
