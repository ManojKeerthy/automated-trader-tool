"""Risk hooks for backtesting engine.

Provides hooks/interfaces for future M4 risk engine logic to:
- Reject an order
- Resize an order
- Block new exposure

Includes a BasicCapitalGuard for M2 research.
"""
from decimal import Decimal
from typing import Protocol

from tradecraft.backtesting.execution import OrderIntent
from tradecraft.backtesting.portfolio import Portfolio


class RiskHook(Protocol):
    """Protocol for risk engine hooks in backtesting."""

    def filter_order(self, order: OrderIntent, portfolio: Portfolio) -> OrderIntent | None:
        """Inspect and optionally resize or reject an order.

        Returns modified OrderIntent, or None to reject.
        """
        ...


class BasicCapitalGuard:
    """Minimal capital and exposure safeguard for M2 research.

    Enforces:
    - Max 20% single-stock capital allocation limit per position
    - Rejects orders if available cash is zero
    """

    def __init__(self, max_single_stock_pct: float = 0.20):
        self.max_single_stock_pct = max_single_stock_pct

    def filter_order(self, order: OrderIntent, portfolio: Portfolio) -> OrderIntent | None:
        if portfolio.cash <= 0:
            return None

        # Calculate max allowable capital for a single position
        max_capital = portfolio.total_equity * Decimal(str(self.max_single_stock_pct))

        # Check existing position value if any
        existing_val = Decimal("0")
        if order.instrument_id in portfolio.positions:
            existing_val = portfolio.positions[order.instrument_id].market_value

        avail_capital_for_stock = max_capital - existing_val
        if avail_capital_for_stock <= 0:
            return None

        return order
