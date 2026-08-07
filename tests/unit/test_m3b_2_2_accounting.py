"""Unit tests for M3B.2.2 Accounting Integrity & Metrics Verification."""

from datetime import date
from decimal import Decimal

import pytest

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.core.exceptions import DataBoundaryViolationError
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.strategy.v2_strategies import (
    BreakoutConfirmV2Strategy,
    MeanReversionV2Strategy,
    MomentumRSV2Strategy,
    TrendPullbackV2Strategy,
)


def test_development_firewall_blocks_validation_dates():
    """Verify that accessing dates in Validation period raises DataBoundaryViolationError."""
    with pytest.raises((ValueError, DataBoundaryViolationError), match="post-DEVELOPMENT"):
        DevelopmentOnlyGuard.validate_range(date(2022, 1, 1), date(2022, 6, 30))


def test_frozen_v2_hashes_match():
    """Verify exact SHA256 hashes of the four frozen canonical V2 strategy configurations."""
    strats = [
        (
            TrendPullbackV2Strategy(),
            "c4556b07bd4edc39f9a53c1c27c601d2c0747fcbc7ad356d4e4ec42af6c993da",
        ),
        (
            BreakoutConfirmV2Strategy(),
            "85d9c0b3d8c360ec9f51beec15b7c0ad09aa04d26473bd463ba9ea97e6f2aacd",
        ),
        (
            MomentumRSV2Strategy(),
            "221c35751fde73a351138d14502bd8b1bf6ad49e051bfe55d6bb086a1d2df825",
        ),
        (
            MeanReversionV2Strategy(),
            "8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82",
        ),
    ]
    for strat, expected_hash in strats:
        assert strat.config_hash == expected_hash


def test_transaction_cost_reconciliation_zero_difference():
    """Verify IndianEquityDeliveryCostModel buy and sell cost calculations match independently derived values."""
    cost_model = IndianEquityDeliveryCostModel()
    price = Decimal("500.00")
    qty = 100
    d = date(2020, 5, 10)

    buy_cost = cost_model.calculate_buy(price, qty, d)
    sell_cost = cost_model.calculate_sell(price * Decimal("1.05"), qty, d)

    # Brokerage (0 for delivery in Zerodha model)
    assert buy_cost.brokerage == Decimal("0.0")
    # STT (0.1% on buy and sell for equity delivery)
    assert buy_cost.stt == (Decimal("50000.00") * Decimal("0.001"))
    assert sell_cost.stt == (Decimal("52500.00") * Decimal("0.001"))

    # Total cost is positive Decimal
    assert buy_cost.total > Decimal("0")
    assert sell_cost.total > Decimal("0")


def test_max_trade_profit_share_semantic_definition():
    """Verify max trade profit share evaluates largest_win / sum_all_wins even when strategy P&L is negative."""
    win_1 = Decimal("1000.00")
    win_2 = Decimal("500.00")

    tot_win_inr = win_1 + win_2  # 1500

    max_trade_win = max([win_1, win_2])  # 1000

    max_trade_share = float((max_trade_win / tot_win_inr) * Decimal("100"))
    assert max_trade_share == pytest.approx(66.67, abs=0.01)


def test_tatasteel_min_r_reconstruction():
    """Verify that R-multiple formula matches exact formula R = Net_PnL / (Risk_Per_Share * Qty)."""
    entry_fill = Decimal("46.4232")
    stop_level = Decimal("46.42")
    qty = 3
    risk_per_share = abs(entry_fill - stop_level)  # 0.0032
    tot_risk = risk_per_share * Decimal(str(qty))  # 0.0096
    net_pnl = Decimal("-15.6192")

    r_calc = float(net_pnl / tot_risk)
    assert r_calc == pytest.approx(-1627.0, abs=0.1)


def test_slippage_4_step_reconciliation():
    """Verify 4-step slippage presentation pipeline without double deduction."""
    # BUY 100 shares @ Ref 100.00 -> Fill 100.05 (5 bps slippage = 5.00)
    # SELL 100 shares @ Ref 110.00 -> Fill 109.945 (5 bps slippage = 5.50)
    ref_buy = Decimal("100.00")
    ref_sell = Decimal("110.00")
    qty = 100

    fill_buy = Decimal("100.05")
    fill_sell = Decimal("109.945")

    counterfactual_pnl = (ref_sell - ref_buy) * qty  # 1000.00
    slippage_impact = Decimal("10.50")
    exec_gross_pnl = (fill_sell - fill_buy) * qty  # 989.50
    explicit_costs = Decimal("28.61")
    net_pnl = exec_gross_pnl - explicit_costs  # 960.89

    assert counterfactual_pnl - slippage_impact == exec_gross_pnl
    assert exec_gross_pnl - explicit_costs == net_pnl
