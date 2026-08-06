"""Portfolio and position state manager for backtesting.

Enforces:
- Exact capital accounting (cash + invested value)
- Integer share tracking (no fractional shares)
- Cash availability verification (no negative cash / no leverage)
- Equity curve tracking & drawdown tracking
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tradecraft.backtesting.costs import CostBreakdown
from tradecraft.backtesting.execution import ExecutionResult


@dataclass
class Position:
    """Represents an open tradeable position."""

    position_id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str
    strategy_id: str
    strategy_version: str
    quantity: int
    avg_entry_price: Decimal
    entry_date: date
    entry_fees: Decimal
    signal_date: date | None = None
    entry_costs_breakdown: CostBreakdown | None = None
    current_stop: Decimal | None = None
    current_target: Decimal | None = None
    unrealised_pnl: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")

    # --- Risk provenance (defect F2). Captured at ENTRY and never mutated afterwards. ---
    # `current_stop` may be trailed by a strategy; `initial_stop` must not be, because the
    # R-multiple denominator is defined by the risk taken when the position was opened.
    initial_stop: Decimal | None = None
    initial_risk_per_share: Decimal | None = None

    # --- Time-stop state (defect F3). Enforced by the engine, not by strategy metadata. ---
    # Previously `max_holding_days` lived in SignalIntent.metadata and was never read by
    # anything, so no position could ever exit on time. See REPO_AUDIT_2026-08-06 §3.
    max_holding_days: int | None = None
    bars_held: int = 0

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.avg_entry_price

    @property
    def is_time_stop_due(self) -> bool:
        """True when the position has been held for its full permitted session count."""
        return self.max_holding_days is not None and self.bars_held >= self.max_holding_days

    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.current_price


@dataclass(frozen=True)
class EquitySnapshot:
    """Historical snapshot of portfolio equity on a given session date."""

    trading_date: date
    cash: Decimal
    invested: Decimal
    total_equity: Decimal
    peak_equity: Decimal
    drawdown_pct: Decimal
    open_positions: int


class Portfolio:
    """Tracks portfolio cash, open positions, realized P&L, and equity curve."""

    def __init__(self, initial_capital: Decimal = Decimal("50000.00")):
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[uuid.UUID, Position] = {}  # instrument_id -> Position
        self.realised_pnl = Decimal("0")
        self.total_fees_paid = Decimal("0")
        self.peak_equity = initial_capital
        self.equity_curve: list[EquitySnapshot] = []

    @property
    def total_equity(self) -> Decimal:
        invested = sum((p.market_value for p in self.positions.values()), Decimal("0"))
        return self.cash + invested

    @property
    def current_drawdown(self) -> Decimal:
        eq = self.total_equity
        if self.peak_equity <= 0:
            return Decimal("0")
        if eq >= self.peak_equity:
            return Decimal("0")
        return ((self.peak_equity - eq) / self.peak_equity) * Decimal("100")

    def process_entry_fill(
        self, execution: ExecutionResult, symbol: str, signal_date: date | None = None
    ) -> Position:
        """Record a successful position entry fill. Returns Position object."""
        assert execution.fill_price is not None
        assert execution.filled

        total_cost = (execution.fill_price * execution.quantity) + execution.costs.total

        if total_cost > self.cash:
            raise ValueError(
                f"Insufficient cash for entry: required ₹{total_cost:.2f}, available ₹{self.cash:.2f}"
            )

        self.cash -= total_cost
        self.total_fees_paid += execution.costs.total

        inst_id = execution.order_intent.instrument_id
        sig_dt = signal_date or execution.order_intent.signal_date

        if inst_id in self.positions:
            # Average into existing position
            pos = self.positions[inst_id]
            total_qty = pos.quantity + execution.quantity
            total_basis = pos.cost_basis + (execution.fill_price * execution.quantity)
            pos.quantity = total_qty
            pos.avg_entry_price = total_basis / total_qty
            pos.entry_fees += execution.costs.total
            if pos.entry_costs_breakdown:
                pos.entry_costs_breakdown = CostBreakdown(
                    brokerage=pos.entry_costs_breakdown.brokerage + execution.costs.brokerage,
                    stt=pos.entry_costs_breakdown.stt + execution.costs.stt,
                    exchange_charges=pos.entry_costs_breakdown.exchange_charges
                    + execution.costs.exchange_charges,
                    gst=pos.entry_costs_breakdown.gst + execution.costs.gst,
                    sebi_fee=pos.entry_costs_breakdown.sebi_fee + execution.costs.sebi_fee,
                    stamp_duty=pos.entry_costs_breakdown.stamp_duty + execution.costs.stamp_duty,
                    dp_charges=pos.entry_costs_breakdown.dp_charges + execution.costs.dp_charges,
                    total=pos.entry_costs_breakdown.total + execution.costs.total,
                )
            else:
                pos.entry_costs_breakdown = execution.costs
            pos.current_stop = execution.order_intent.stop_loss_level or pos.current_stop
            pos.current_target = execution.order_intent.target_level or pos.current_target
            # Averaging in changes the entry basis, so the entry-time risk distance is
            # recomputed against the new average. `initial_stop` itself is left alone.
            if pos.initial_stop is not None:
                pos.initial_risk_per_share = abs(pos.avg_entry_price - pos.initial_stop)
            return pos
        else:
            initial_stop = execution.order_intent.stop_loss_level
            pos = Position(
                position_id=uuid.uuid4(),
                instrument_id=inst_id,
                symbol=symbol,
                strategy_id=execution.order_intent.strategy_id,
                strategy_version=execution.order_intent.strategy_version,
                quantity=execution.quantity,
                avg_entry_price=execution.fill_price,
                entry_date=execution.execution_date,
                entry_fees=execution.costs.total,
                signal_date=sig_dt,
                entry_costs_breakdown=execution.costs,
                current_stop=initial_stop,
                current_target=execution.order_intent.target_level,
                current_price=execution.fill_price,
                initial_stop=initial_stop,
                initial_risk_per_share=(
                    abs(execution.fill_price - initial_stop) if initial_stop is not None else None
                ),
                max_holding_days=execution.order_intent.max_holding_days,
            )
            self.positions[inst_id] = pos
            return pos

    def process_exit_fill(self, execution: ExecutionResult) -> Decimal:
        """Record a successful position exit fill. Returns net realized P&L."""
        assert execution.fill_price is not None
        assert execution.filled

        inst_id = execution.order_intent.instrument_id
        if inst_id not in self.positions:
            raise KeyError(f"No open position found for instrument {inst_id}")

        pos = self.positions[inst_id]
        if execution.quantity > pos.quantity:
            raise ValueError(
                f"Cannot exit {execution.quantity} shares: position only holds {pos.quantity}"
            )

        gross_proceeds = execution.fill_price * execution.quantity
        net_proceeds = gross_proceeds - execution.costs.total

        self.cash += net_proceeds
        self.total_fees_paid += execution.costs.total

        cost_of_shares_sold = pos.avg_entry_price * execution.quantity
        net_pnl = net_proceeds - (cost_of_shares_sold + pos.entry_fees)
        self.realised_pnl += net_pnl

        pos.quantity -= execution.quantity
        if pos.quantity == 0:
            del self.positions[inst_id]

        return net_pnl

    def mark_to_market(
        self, trading_date: date, prices: dict[uuid.UUID, Decimal]
    ) -> EquitySnapshot:
        """Update open position mark-to-market prices and record equity snapshot."""
        invested = Decimal("0")
        for inst_id, pos in self.positions.items():
            if inst_id in prices:
                pos.current_price = prices[inst_id]
                pos.unrealised_pnl = (pos.current_price - pos.avg_entry_price) * pos.quantity
            invested += pos.market_value

        total_eq = self.cash + invested
        if total_eq > self.peak_equity:
            self.peak_equity = total_eq

        drawdown = self.current_drawdown

        snapshot = EquitySnapshot(
            trading_date=trading_date,
            cash=self.cash,
            invested=invested,
            total_equity=total_eq,
            peak_equity=self.peak_equity,
            drawdown_pct=drawdown,
            open_positions=len(self.positions),
        )
        self.equity_curve.append(snapshot)
        return snapshot
