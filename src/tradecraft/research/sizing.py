"""Research Position Sizing Engine for M3B Backtests.

IMPORTANT:
RESEARCH SIZING ASSUMPTION — NOT M4 RISK POLICY.
This sizing module implements a deterministic 10% equal-capital allocation
to evaluate and compare strategies fairly during research.
"""

import math
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SizingResult:
    """Result of research position sizing calculation."""

    quantity: int
    estimated_cost: Decimal
    required_cash: Decimal
    is_valid: bool
    rejection_reason: str = ""


class ResearchSizingCalculator:
    """Calculates position quantity at execution T+1 using actual fill price."""

    def __init__(
        self,
        allocation_pct: Decimal = Decimal("0.10"),
        max_concurrent_positions: int = 10,
    ):
        self.allocation_pct = allocation_pct
        self.max_concurrent_positions = max_concurrent_positions

    def calculate_quantity(
        self,
        portfolio_equity: Decimal,
        available_cash: Decimal,
        actual_fill_price: Decimal,
        estimated_transaction_cost: Decimal = Decimal("0.0"),
    ) -> SizingResult:
        """Calculates integer share quantity using actual T+1 fill price.

        Guarantees:
        - Whole integer shares only (floor division, quantity >= 1)
        - Actual required cash (fill * quantity + costs) <= available cash
        - Zero fractional shares
        - Zero negative cash
        - Zero leverage
        """
        if actual_fill_price <= Decimal("0.0") or portfolio_equity <= Decimal("0.0"):
            return SizingResult(
                quantity=0,
                estimated_cost=Decimal("0.0"),
                required_cash=Decimal("0.0"),
                is_valid=False,
                rejection_reason="INVALID_PRICE_OR_EQUITY",
            )

        target_allocation = portfolio_equity * self.allocation_pct
        raw_quantity = int(math.floor(float(target_allocation / actual_fill_price)))

        if raw_quantity < 1:
            return SizingResult(
                quantity=0,
                estimated_cost=Decimal("0.0"),
                required_cash=Decimal("0.0"),
                is_valid=False,
                rejection_reason="QUANTITY_LESS_THAN_ONE",
            )

        # Iteratively cap quantity to guarantee cash sufficiency including costs
        qty = raw_quantity
        while qty >= 1:
            notional = actual_fill_price * Decimal(str(qty))
            total_cash_needed = notional + estimated_transaction_cost
            if total_cash_needed <= available_cash:
                return SizingResult(
                    quantity=qty,
                    estimated_cost=estimated_transaction_cost,
                    required_cash=total_cash_needed,
                    is_valid=True,
                    rejection_reason="",
                )
            qty -= 1

        return SizingResult(
            quantity=0,
            estimated_cost=Decimal("0.0"),
            required_cash=Decimal("0.0"),
            is_valid=False,
            rejection_reason="SKIPPED_INSUFFICIENT_CASH",
        )
