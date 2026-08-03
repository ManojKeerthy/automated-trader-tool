"""Unit tests for M3B.2.1 Signal-to-Execution Pipeline Defect & Fix Verification."""

import uuid
from datetime import date
from decimal import Decimal

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.execution import ExecutionSimulator, OrderIntent
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.research.sizing import ResearchSizingCalculator


def test_unsized_order_intent_rejected_without_sizer():
    """Verify that OrderIntent with quantity_hint=None is rejected by ExecutionSimulator."""
    sim = ExecutionSimulator(IndianEquityDeliveryCostModel(), FixedBasisPointSlippage(bps=5))
    order = OrderIntent(
        order_id=uuid.uuid4(),
        strategy_id="strat_test",
        strategy_version="1.0.0",
        instrument_id=uuid.uuid4(),
        direction="BUY",
        order_type="MARKET",
        signal_date=date(2020, 1, 1),
        quantity_hint=None,
    )
    bar = {
        "open": Decimal("100.00"),
        "high": Decimal("105.00"),
        "low": Decimal("99.00"),
        "close": Decimal("104.00"),
    }
    res = sim.simulate_entry_execution(order, bar, date(2020, 1, 2), Decimal("100000.00"))

    assert not res.filled
    assert res.rejection_reason == "Invalid or zero share quantity requested"


def test_research_sizing_calculator_calculates_valid_quantity():
    """Verify that ResearchSizingCalculator produces integer share quantity at 10% allocation."""
    sizer = ResearchSizingCalculator(allocation_pct=Decimal("0.10"))
    res = sizer.calculate_quantity(
        portfolio_equity=Decimal("1000000.00"),
        available_cash=Decimal("1000000.00"),
        actual_fill_price=Decimal("500.00"),
        estimated_transaction_cost=Decimal("100.00"),
    )

    assert res.is_valid
    assert res.quantity == 200  # (1,000,000 * 0.10) / 500 = 200 shares
    assert res.required_cash <= Decimal("1000000.00")
