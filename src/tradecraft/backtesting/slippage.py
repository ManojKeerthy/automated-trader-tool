"""Slippage models for backtesting execution simulation.

Slippage represents the difference between the theoretical execution price
and the actual simulated fill price. It accounts for market impact, order
book dynamics, and execution latency that cannot be captured in EOD data.

Models:
- ZeroSlippage: Debugging only — fills at exact theoretical price
- FixedBasisPointSlippage: Configurable fixed BPS impact (default 5 bps)

Production-quality strategy evaluation MUST NOT rely solely on zero-slippage results.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol


class SlippageModel(Protocol):
    """Protocol for slippage calculation."""

    @property
    def name(self) -> str: ...

    def apply(self, price: Decimal, side: str, quantity: int) -> Decimal:
        """Apply slippage to a theoretical execution price.

        Args:
            price: Theoretical fill price
            side: 'BUY' or 'SELL'
            quantity: Number of shares (for future liquidity-based models)

        Returns:
            Adjusted price after slippage (higher for BUY, lower for SELL)
        """
        ...


class ZeroSlippage:
    """Zero slippage model — for debugging and comparison ONLY.

    WARNING: Production-quality research must not rely solely on
    zero-slippage results. Use FixedBasisPointSlippage or better.
    """

    @property
    def name(self) -> str:
        return "zero_slippage_debug_only"

    def apply(self, price: Decimal, side: str, quantity: int) -> Decimal:
        return price


class FixedBasisPointSlippage:
    """Fixed basis-point slippage applied to every fill.

    Default: 5 bps (0.05%) which is conservative for Nifty 50 large-cap stocks.

    BUY: price increases by bps (worse fill)
    SELL: price decreases by bps (worse fill)
    """

    def __init__(self, bps: int = 5):
        if bps < 0:
            raise ValueError("Slippage basis points must be non-negative")
        self._bps = bps
        self._factor = Decimal(str(bps)) / Decimal("10000")

    @property
    def name(self) -> str:
        return f"fixed_{self._bps}bps"

    def apply(self, price: Decimal, side: str, quantity: int) -> Decimal:
        slippage_amount = (price * self._factor).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        if side == "BUY":
            return price + slippage_amount
        elif side == "SELL":
            return price - slippage_amount
        else:
            raise ValueError(f"Unknown side: {side}. Must be 'BUY' or 'SELL'.")
