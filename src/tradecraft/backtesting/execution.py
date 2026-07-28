"""Realistic EOD Execution Simulator for Backtesting.

Models execution semantics per approved specification and amendments:
- Signal timing: Strategy evaluates on session T close -> earliest execution at session T+1.
- Market orders fill at T+1 OPEN modified by slippage.
- Limit orders fill if T+1 LOW <= limit_price (buy). Fills at min(open, limit_price).
- Stop orders:
  - Intraday trigger: if T+1 LOW <= stop_trigger <= T+1 HIGH, triggers and fills at stop_trigger.
  - Gap-through-stop: if T+1 OPEN < stop_trigger (for sell stop) or OPEN > stop_trigger (for buy stop),
    fills at OPEN (not at stop_trigger!).
- OHLC Ambiguity Handling:
  - When BOTH a stop-loss and a target-price fall within the same daily bar's HIGH-LOW range,
    the simulator deterministically assumes the ADVERSE outcome (stop-loss hit first).
- Fractional shares: Strictly prohibited. Enforces integer share quantities.
- Capital constraints: Rejects order if required capital exceeds available cash.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.costs import CostBreakdown, CostModel
from tradecraft.backtesting.slippage import SlippageModel
from tradecraft.strategy.base import ExitSignal

logger = logging.getLogger(__name__)


@dataclass
class OrderIntent:
    """An active order intent queued for execution on session T+1."""

    order_id: uuid.UUID
    strategy_id: str
    strategy_version: str
    instrument_id: uuid.UUID
    direction: str  # 'BUY'
    order_type: str  # 'MARKET', 'LIMIT', 'STOP'
    signal_date: date
    limit_price: Decimal | None = None
    stop_trigger: Decimal | None = None
    stop_loss_level: Decimal | None = None
    target_level: Decimal | None = None
    quantity_hint: int | None = None
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of an order execution attempt on session T+1."""

    order_intent: OrderIntent
    execution_date: date
    filled: bool
    fill_price: Decimal | None = None
    quantity: int = 0
    slippage_cost: Decimal = Decimal("0")
    costs: CostBreakdown = field(default_factory=CostBreakdown)
    rejection_reason: str | None = None
    exit_reason: str | None = None  # e.g., 'STOP_LOSS', 'PROFIT_TARGET', 'STRATEGY_SIGNAL'
    is_ambiguous_bar: bool = False  # True if both stop & target were touched on same bar


class ExecutionSimulator:
    """Simulates realistic order execution for EOD swing trading."""

    def __init__(
        self,
        cost_model: CostModel,
        slippage_model: SlippageModel,
    ):
        self.cost_model = cost_model
        self.slippage_model = slippage_model

    def simulate_entry_execution(
        self,
        order: OrderIntent,
        bar: dict[str, Any],
        execution_date: date,
        available_cash: Decimal,
    ) -> ExecutionResult:
        """Simulate entry order execution on session T+1 bar.

        Enforces whole-share integer sizing and cash availability checks.
        """
        o = bar["open"]
        h = bar["high"]
        low_p = bar["low"]

        # 1. Determine theoretical fill price based on order type
        fill_price: Decimal | None = None

        if order.order_type == "MARKET":
            fill_price = o
        elif order.order_type == "LIMIT":
            assert order.limit_price is not None
            if low_p <= order.limit_price:
                # Fill at better of Open or Limit
                fill_price = min(o, order.limit_price)
            else:
                return ExecutionResult(
                    order_intent=order,
                    execution_date=execution_date,
                    filled=False,
                    rejection_reason="Limit price not reached (low > limit_price)",
                )
        elif order.order_type == "STOP":
            assert order.stop_trigger is not None
            if h >= order.stop_trigger:
                # Gap above stop or intraday trigger
                fill_price = max(o, order.stop_trigger)
            else:
                return ExecutionResult(
                    order_intent=order,
                    execution_date=execution_date,
                    filled=False,
                    rejection_reason="Stop trigger not reached (high < stop_trigger)",
                )

        # Apply slippage
        assert fill_price is not None
        actual_fill_price = self.slippage_model.apply(fill_price, order.direction, 0)
        slippage_per_share = abs(actual_fill_price - fill_price)

        # Determine quantity (integer shares only)
        quantity = order.quantity_hint or 0
        if quantity <= 0:
            return ExecutionResult(
                order_intent=order,
                execution_date=execution_date,
                filled=False,
                rejection_reason="Invalid or zero share quantity requested",
            )

        # Estimate costs to verify capital constraint
        cost_breakdown = self.cost_model.calculate_buy(actual_fill_price, quantity, execution_date)
        total_required_cash = (actual_fill_price * quantity) + cost_breakdown.total

        if total_required_cash > available_cash:
            # Resize quantity downward to fit cash if possible, or reject
            max_qty = int(available_cash // actual_fill_price)
            if max_qty >= 1:
                # Recalculate with resized quantity
                quantity = max_qty
                cost_breakdown = self.cost_model.calculate_buy(
                    actual_fill_price, quantity, execution_date
                )
                total_required_cash = (actual_fill_price * quantity) + cost_breakdown.total
                if total_required_cash > available_cash and quantity > 1:
                    quantity -= 1
                    cost_breakdown = self.cost_model.calculate_buy(
                        actual_fill_price, quantity, execution_date
                    )
            else:
                return ExecutionResult(
                    order_intent=order,
                    execution_date=execution_date,
                    filled=False,
                    rejection_reason=f"Insufficient cash (required ~₹{total_required_cash:.2f}, available ₹{available_cash:.2f})",
                )

        slippage_total = slippage_per_share * quantity

        return ExecutionResult(
            order_intent=order,
            execution_date=execution_date,
            filled=True,
            fill_price=actual_fill_price,
            quantity=quantity,
            slippage_cost=slippage_total,
            costs=cost_breakdown,
        )

    def simulate_exit_execution(
        self,
        position_id: uuid.UUID,
        strategy_id: str,
        strategy_version: str,
        instrument_id: uuid.UUID,
        quantity: int,
        stop_loss_level: Decimal | None,
        target_level: Decimal | None,
        exit_signal: ExitSignal | None,
        bar: dict[str, Any],
        execution_date: date,
        is_first_isin_sell_today: bool = True,
    ) -> ExecutionResult | None:
        """Simulate protective stops, target exits, or signal exits on session bar.

        OHLC Ambiguity Handling:
        If BOTH stop-loss and profit-target fall inside [Low, High], assume ADVERSE (stop-loss hit first).
        Gap-through-stop Handling:
        If Open < stop_loss_level, fill at Open (gap down).
        """
        o = bar["open"]
        h = bar["high"]
        low_p = bar["low"]

        dummy_order = OrderIntent(
            order_id=uuid.uuid4(),
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            instrument_id=instrument_id,
            direction="BUY",
            order_type="MARKET",
            signal_date=execution_date,
            quantity_hint=quantity,
        )

        stop_hit = False
        target_hit = False
        is_ambiguous = False

        if stop_loss_level is not None and low_p <= stop_loss_level:
            stop_hit = True

        if target_level is not None and h >= target_level:
            target_hit = True

        # Check OHLC Ambiguity
        if stop_hit and target_hit:
            is_ambiguous = True
            # Conservative policy: assume stop-loss was hit first!
            target_hit = False

        fill_price: Decimal | None = None
        exit_reason: str | None = None

        if stop_hit:
            exit_reason = "STOP_LOSS"
            assert stop_loss_level is not None
            fill_price = o if o < stop_loss_level else stop_loss_level
        elif target_hit:
            exit_reason = "PROFIT_TARGET"
            assert target_level is not None
            fill_price = o if o > target_level else target_level
        elif exit_signal is not None:
            exit_reason = exit_signal.reason or "STRATEGY_SIGNAL"
            if exit_signal.exit_type == "MARKET":
                fill_price = o
            elif exit_signal.exit_type == "LIMIT":
                assert exit_signal.limit_price is not None
                if h >= exit_signal.limit_price:
                    fill_price = max(o, exit_signal.limit_price)
                else:
                    return None
            elif exit_signal.exit_type == "STOP":
                assert exit_signal.stop_trigger is not None
                if low_p <= exit_signal.stop_trigger:
                    fill_price = min(o, exit_signal.stop_trigger)
                else:
                    return None

        if fill_price is None or exit_reason is None:
            return None

        # Apply sell slippage
        actual_fill_price = self.slippage_model.apply(fill_price, "SELL", quantity)
        slippage_total = abs(fill_price - actual_fill_price) * quantity

        costs = self.cost_model.calculate_sell(
            actual_fill_price, quantity, execution_date, is_new_isin_today=is_first_isin_sell_today
        )

        return ExecutionResult(
            order_intent=dummy_order,
            execution_date=execution_date,
            filled=True,
            fill_price=actual_fill_price,
            quantity=quantity,
            slippage_cost=slippage_total,
            costs=costs,
            exit_reason=exit_reason,
            is_ambiguous_bar=is_ambiguous,
        )
