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

FIXED-COST-DOMINATED MICRO-POSITIONS (defect F7, 2026-08-06)
==============================================================
The cash-fitting loop below (`while qty >= 1: ... qty -= 1`) had no floor: when available
cash was nearly exhausted (routine with several concurrent positions open), it would shrink
a position all the way down to a handful of shares - even 1 - rather than rejecting the
trade. Found running Phase C on real data: 15.7% of TrendPullbackV2's DEVELOPMENT trades had
total risk (risk_per_share x quantity) under Rs 30, and the 15 worst R-multiples in the run
(as low as -31.5R) were *all* quantity<=5 positions losing almost exactly Rs 14-17 regardless
of which direction the price moved - the flat DP/brokerage charge (~Rs 13-18 per this
project's own cost model), not a real trading loss. A 1-share position with ~Rs 0.50 of
price-based risk cannot economically absorb a ~Rs 15 fixed cost; R-multiple for such a trade
is dominated by fee structure, not edge, and contaminates `expectancy_r` for the whole
strategy. `calculate_quantity` now rejects (`POSITION_TOO_SMALL_RELATIVE_TO_COSTS`) rather
than accepting a cash-starved position whose risk can't clear a floor tied to the actual
estimated transaction cost for that trade.

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

    # A trade's total risk (risk_per_share x quantity) must clear this multiple of its own
    # estimated transaction cost, so a full stop-out loss is dominated by genuine price risk
    # rather than by flat fees. 10x is a round, conservative number - it does not come from
    # tuning against any backtest result, only from wanting fixed costs to be a clearly minor
    # component (<=10%) of a worst-case loss. See "FIXED-COST-DOMINATED MICRO-POSITIONS"
    # above for the real trades (losing ~Rs 15 on a 1-share position regardless of price
    # direction) that this exists to prevent.
    MIN_RISK_TO_TRANSACTION_COST_RATIO = Decimal("10")
    # Floor even when estimated_transaction_cost is reported as 0 (e.g. not yet estimated at
    # sizing time) - Rs 200 is comfortably above the ~Rs 15-18 flat DP/brokerage charge this
    # project's own cost model documents (CLAUDE.md: "DP charges ~Rs 13+GST"), so it cannot
    # itself become the binding constraint in the common case.
    ABSOLUTE_MIN_TOTAL_RISK_INR = Decimal("200")

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

        # Fit within available cash including costs. Once cash-fitting has reduced qty to
        # the point where total risk can't clear the cost floor, no smaller qty will fix
        # it either (risk only shrinks further) - reject immediately rather than accepting
        # a fee-dominated micro-position (defect F7, see class docstring above).
        min_risk_floor = max(
            estimated_transaction_cost * self.MIN_RISK_TO_TRANSACTION_COST_RATIO,
            self.ABSOLUTE_MIN_TOTAL_RISK_INR,
        )
        while qty >= 1:
            needed = (actual_fill_price * Decimal(str(qty))) + estimated_transaction_cost
            if needed <= available_cash:
                if risk_per_share * Decimal(str(qty)) < min_risk_floor:
                    return SizingResult(
                        0, Decimal("0"), Decimal("0"), False, "POSITION_TOO_SMALL_RELATIVE_TO_COSTS"
                    )
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
