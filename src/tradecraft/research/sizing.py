"""Research Position Sizing Engines for backtests.

IMPORTANT:
RESEARCH SIZING ASSUMPTION — NOT M4 RISK POLICY.

Two calculators are provided:

`RiskBasedSizingCalculator` (DEFAULT, recommended)
    Fixed-fractional risk: quantity = (equity x risk_pct) / (entry - stop).
    Every trade risks the same fraction of equity, so R-multiples are comparable across
    trades and the portfolio is not silently concentrated in low-volatility names.

`ResearchSizingCalculator` (LEGACY, retained for reproducing historical runs)
    Fixed 10% notional allocation regardless of stop distance.

WHY THE DEFAULT CHANGED (defect F4, 2026-08-06)
===============================================
The legacy calculator allocated 10% of equity to every position irrespective of where the
stop sat. A name with a 2% stop and a name with an 8% stop both received 10% of capital, so
realised risk per trade varied roughly fourfold. Consequences:

- R-multiples were not comparable between trades, making `expectancy_r` (a mean of R across
  trades) meaningless even before the plumbing defects F2/F2b.
- Portfolio outcomes were dominated by whichever names happened to have tight stops. In the
  Cycle 1 evidence a single instrument contributed 42.9% of all P&L.

Additionally `max_concurrent_positions` was a constructor parameter that the engine never
passed and never enforced — the 10-holding cap documented in DEC-002 did not exist in code.
Concurrency was limited only incidentally, by running out of cash, which also produced
ragged part-filled positions (observed notionals ranging from Rs 60,072 to Rs 103,562 for a
nominally uniform allocation).

See docs/research/REPO_AUDIT_2026-08-06.md section 4.
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


class RiskBasedSizingCalculator:
    """Fixed-fractional risk sizing: every trade risks the same fraction of equity.

    quantity = floor((equity * risk_pct) / |entry - stop|)

    Then capped by:
      - `max_position_pct` of equity as notional (stops the calculator from taking an
        enormous position in a name with a very tight stop)
      - available cash including transaction costs

    A signal with no stop cannot be sized by risk. Rather than silently falling back to a
    notional allocation — which would reintroduce the very defect this class exists to fix —
    it is rejected with NO_STOP_PROVIDED. Strategies must declare their risk.
    """

    def __init__(
        self,
        risk_pct: Decimal = Decimal("0.01"),
        max_position_pct: Decimal = Decimal("0.20"),
        max_concurrent_positions: int = 10,
    ):
        if risk_pct <= Decimal("0") or risk_pct > Decimal("0.10"):
            raise ValueError(f"risk_pct must be in (0, 0.10], got {risk_pct}")
        self.risk_pct = risk_pct
        self.max_position_pct = max_position_pct
        self.max_concurrent_positions = max_concurrent_positions

    @property
    def version(self) -> str:
        return (
            f"risk_based_v1:risk_pct={self.risk_pct}:"
            f"max_pos_pct={self.max_position_pct}:max_pos={self.max_concurrent_positions}"
        )

    def calculate_quantity(
        self,
        portfolio_equity: Decimal,
        available_cash: Decimal,
        actual_fill_price: Decimal,
        stop_loss_level: Decimal | None = None,
        estimated_transaction_cost: Decimal = Decimal("0.0"),
    ) -> SizingResult:
        """Size the position by risk. Returns quantity 0 with a reason if not sizeable."""
        if actual_fill_price <= Decimal("0.0") or portfolio_equity <= Decimal("0.0"):
            return SizingResult(0, Decimal("0"), Decimal("0"), False, "INVALID_PRICE_OR_EQUITY")

        if stop_loss_level is None:
            return SizingResult(0, Decimal("0"), Decimal("0"), False, "NO_STOP_PROVIDED")

        risk_per_share = abs(actual_fill_price - stop_loss_level)
        if risk_per_share <= Decimal("0"):
            return SizingResult(0, Decimal("0"), Decimal("0"), False, "ZERO_RISK_DISTANCE")

        # Guard against a stop so tight it implies an absurd position (the T+1 gap problem:
        # the stop is anchored to the prior close but the fill is the next open).
        if risk_per_share < actual_fill_price * Decimal("0.005"):
            return SizingResult(0, Decimal("0"), Decimal("0"), False, "DEGENERATE_RISK_DISTANCE")

        risk_budget = portfolio_equity * self.risk_pct
        qty = int(math.floor(float(risk_budget / risk_per_share)))

        # Cap notional exposure
        max_notional = portfolio_equity * self.max_position_pct
        qty = min(qty, int(math.floor(float(max_notional / actual_fill_price))))

        if qty < 1:
            return SizingResult(0, Decimal("0"), Decimal("0"), False, "QUANTITY_LESS_THAN_ONE")

        # Fit within available cash including costs
        while qty >= 1:
            needed = (actual_fill_price * Decimal(str(qty))) + estimated_transaction_cost
            if needed <= available_cash:
                return SizingResult(qty, estimated_transaction_cost, needed, True, "")
            qty -= 1

        return SizingResult(0, Decimal("0"), Decimal("0"), False, "SKIPPED_INSUFFICIENT_CASH")


class ResearchSizingCalculator:
    """LEGACY: fixed 10% notional allocation, ignoring stop distance.

    Retained only to reproduce pre-2026-08-06 runs. Do not use for new research — it makes
    per-trade risk vary with stop distance and therefore makes R-multiples incomparable.
    Use `RiskBasedSizingCalculator` instead.
    """

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
