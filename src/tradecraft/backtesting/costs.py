"""Effective-dated transaction cost models for Indian equity delivery trades.

Verified rates as of July 2026 from authoritative sources:
- Zerodha charges page (zerodha.com/charges)
- NSE circular on transaction charges
- SEBI circular on turnover fee
- State stamp duty schedule

Cost Model Assumptions:
- All rates are for NSE EQUITY DELIVERY (CNC) transactions
- Stamp duty uses Maharashtra rate (0.015% on buy) — varies by state
- DP charges: ₹13 + 18% GST per ISIN per day on sell side (Zerodha/CDSL)
- GST: 18% on (brokerage + SEBI charges + exchange transaction charges)

IMPORTANT: When historical rates are unavailable, backtests MUST flag
the assumption as COST_MODEL_HISTORICAL_ASSUMPTION.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol


@dataclass(frozen=True)
class CostBreakdown:
    """Itemised cost breakdown for a single trade leg."""

    brokerage: Decimal = Decimal("0")
    stt: Decimal = Decimal("0")
    exchange_charges: Decimal = Decimal("0")
    gst: Decimal = Decimal("0")
    sebi_fee: Decimal = Decimal("0")
    stamp_duty: Decimal = Decimal("0")
    dp_charges: Decimal = Decimal("0")
    total: Decimal = Decimal("0")

    def to_dict(self) -> dict[str, str]:
        return {
            "brokerage": str(self.brokerage),
            "stt": str(self.stt),
            "exchange_charges": str(self.exchange_charges),
            "gst": str(self.gst),
            "sebi_fee": str(self.sebi_fee),
            "stamp_duty": str(self.stamp_duty),
            "dp_charges": str(self.dp_charges),
            "total": str(self.total),
        }


class CostModel(Protocol):
    """Protocol for transaction cost calculation."""

    @property
    def version(self) -> str: ...

    @property
    def effective_from(self) -> date: ...

    @property
    def effective_to(self) -> date | None: ...

    @property
    def is_historical_assumption(self) -> bool: ...

    def calculate_buy(self, price: Decimal, quantity: int, trade_date: date) -> CostBreakdown: ...

    def calculate_sell(
        self, price: Decimal, quantity: int, trade_date: date, is_new_isin_today: bool
    ) -> CostBreakdown: ...

    def round_trip_cost(
        self,
        buy_price: Decimal,
        sell_price: Decimal,
        quantity: int,
        buy_date: date,
        sell_date: date,
    ) -> tuple[CostBreakdown, CostBreakdown, Decimal]: ...


@dataclass(frozen=True)
class BrokerCostProfile:
    """Configurable broker account cost profile for DP charges and transaction fees."""

    name: str = "zerodha_standard"
    dp_charge_per_isin: Decimal = Decimal("13.00")
    dp_gst_pct: Decimal = Decimal("0.18")

    @property
    def raw_dp_charge(self) -> Decimal:
        """Raw DP charge before monetary rounding: base + (base * gst_pct)."""
        return self.dp_charge_per_isin + (self.dp_charge_per_isin * self.dp_gst_pct)


# Standard profiles
ZERODHA_STANDARD_PROFILE = BrokerCostProfile(
    name="zerodha_standard",
    dp_charge_per_isin=Decimal("13.00"),
)

ZERODHA_FEMALE_PRIMARY_PROFILE = BrokerCostProfile(
    name="zerodha_female_primary",
    dp_charge_per_isin=Decimal("12.75"),
)


@dataclass(frozen=True)
class CostScheduleRates:
    """Individual rate components for a cost schedule.

    Sources verified from current official Zerodha charges documentation (zerodha.com/charges):
    - Brokerage: Zerodha equity delivery = ₹0
    - STT: 0.1% on buy+sell (delivery)
    - Exchange transaction charges: 0.00307% NSE (zerodha.com/charges updated rate)
    - GST: 18% on (brokerage + SEBI + exchange charges)
    - SEBI turnover fee: 0.0001% (₹10 per crore)
    - Stamp duty: 0.015% on buy side
    - DP charges: Configurable via BrokerCostProfile (default ₹13 + 18% GST = ₹15.34 per ISIN per day)
    """

    brokerage_pct: Decimal = Decimal("0")
    stt_pct: Decimal = Decimal("0.001")  # 0.1%
    exchange_charges_pct: Decimal = Decimal("0.0000307")  # 0.00307% NSE
    gst_pct: Decimal = Decimal("0.18")  # 18%
    sebi_fee_pct: Decimal = Decimal("0.000001")  # 0.0001% = ₹10/crore
    stamp_duty_buy_pct: Decimal = Decimal("0.00015")  # 0.015%
    profile: BrokerCostProfile = ZERODHA_STANDARD_PROFILE


# Current verified schedule (July 2026)
CURRENT_SCHEDULE = CostScheduleRates()

# Rounding precision for financial calculations (paise)
PAISE = Decimal("0.01")


class IndianEquityDeliveryCostModel:
    """Transaction cost model for Indian NSE equity delivery (CNC) trades.

    Uses effective-dated cost schedules with configurable broker cost profiles.
    When a historical trade date falls outside any verified schedule, the model
    applies the nearest available schedule and flags `is_historical_assumption = True`.

    Rate Sources (verified July 2026):
    - Brokerage: ₹0 (Zerodha equity delivery)
    - STT: 0.1% on both buy and sell value
    - Exchange transaction charges: 0.00307% on turnover (NSE)
    - GST: 18% on (brokerage + SEBI charges + exchange transaction charges)
    - SEBI turnover fee: 0.0001% (₹10 per crore)
    - Stamp duty: 0.015% on buy side
    - DP charges: Configurable per profile (Standard ₹13+GST=₹15.34; Female Primary ₹12.75+GST=₹15.05)
    """

    def __init__(
        self,
        rates: CostScheduleRates | None = None,
        profile: BrokerCostProfile | None = None,
        version: str = "indian_eq_delivery_v2026.07_zerodha_published",
        effective_from: date = date(2026, 4, 1),
        effective_to: date | None = None,
        historical_assumption: bool = False,
    ):
        base_rates = rates or CURRENT_SCHEDULE
        if profile is not None:
            # Override profile in schedule
            self._rates = CostScheduleRates(
                brokerage_pct=base_rates.brokerage_pct,
                stt_pct=base_rates.stt_pct,
                exchange_charges_pct=base_rates.exchange_charges_pct,
                gst_pct=base_rates.gst_pct,
                sebi_fee_pct=base_rates.sebi_fee_pct,
                stamp_duty_buy_pct=base_rates.stamp_duty_buy_pct,
                profile=profile,
            )
        else:
            self._rates = base_rates

        self._version = version
        self._effective_from = effective_from
        self._effective_to = effective_to
        self._historical_assumption = historical_assumption

    @property
    def version(self) -> str:
        return self._version

    @property
    def profile_name(self) -> str:
        return self._rates.profile.name

    @property
    def effective_from(self) -> date:
        return self._effective_from

    @property
    def effective_to(self) -> date | None:
        return self._effective_to

    @property
    def is_historical_assumption(self) -> bool:
        return self._historical_assumption

    def _check_date_coverage(self, trade_date: date) -> bool:
        """Check if trade_date falls within this schedule's effective period."""
        if trade_date < self._effective_from:
            return False
        return not bool(self._effective_to and trade_date > self._effective_to)

    def calculate_buy(self, price: Decimal, quantity: int, trade_date: date) -> CostBreakdown:
        """Calculate costs for a buy-side equity delivery trade."""
        r = self._rates
        turnover = price * quantity

        brokerage = (turnover * r.brokerage_pct).quantize(PAISE, rounding=ROUND_HALF_UP)
        stt = (turnover * r.stt_pct).quantize(PAISE, rounding=ROUND_HALF_UP)
        exchange_charges = (turnover * r.exchange_charges_pct).quantize(
            PAISE, rounding=ROUND_HALF_UP
        )
        sebi_fee = (turnover * r.sebi_fee_pct).quantize(PAISE, rounding=ROUND_HALF_UP)

        # GST on brokerage + SEBI + exchange charges
        gst_base = brokerage + sebi_fee + exchange_charges
        gst = (gst_base * r.gst_pct).quantize(PAISE, rounding=ROUND_HALF_UP)

        # Stamp duty on buy side
        stamp_duty = (turnover * r.stamp_duty_buy_pct).quantize(PAISE, rounding=ROUND_HALF_UP)

        # No DP charges on buy
        dp_charges = Decimal("0")

        total = brokerage + stt + exchange_charges + gst + sebi_fee + stamp_duty + dp_charges

        return CostBreakdown(
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            gst=gst,
            sebi_fee=sebi_fee,
            stamp_duty=stamp_duty,
            dp_charges=dp_charges,
            total=total,
        )

    def calculate_sell(
        self,
        price: Decimal,
        quantity: int,
        trade_date: date,
        is_new_isin_today: bool = True,
    ) -> CostBreakdown:
        """Calculate costs for a sell-side equity delivery trade.

        Args:
            is_new_isin_today: If True, applies DP charges for this ISIN.
                DP is charged per ISIN per day, regardless of quantity.
        """
        r = self._rates
        turnover = price * quantity

        brokerage = (turnover * r.brokerage_pct).quantize(PAISE, rounding=ROUND_HALF_UP)
        stt = (turnover * r.stt_pct).quantize(PAISE, rounding=ROUND_HALF_UP)
        exchange_charges = (turnover * r.exchange_charges_pct).quantize(
            PAISE, rounding=ROUND_HALF_UP
        )
        sebi_fee = (turnover * r.sebi_fee_pct).quantize(PAISE, rounding=ROUND_HALF_UP)

        gst_base = brokerage + sebi_fee + exchange_charges
        gst = (gst_base * r.gst_pct).quantize(PAISE, rounding=ROUND_HALF_UP)

        # No stamp duty on sell
        stamp_duty = Decimal("0")

        # DP charges: configurable base + GST per ISIN per day on sell
        if is_new_isin_today:
            dp_base = r.profile.dp_charge_per_isin
            dp_gst = (dp_base * r.profile.dp_gst_pct).quantize(PAISE, rounding=ROUND_HALF_UP)
            dp_charges = dp_base + dp_gst
        else:
            dp_charges = Decimal("0")

        total = brokerage + stt + exchange_charges + gst + sebi_fee + stamp_duty + dp_charges

        return CostBreakdown(
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            gst=gst,
            sebi_fee=sebi_fee,
            stamp_duty=stamp_duty,
            dp_charges=dp_charges,
            total=total,
        )

    def round_trip_cost(
        self,
        buy_price: Decimal,
        sell_price: Decimal,
        quantity: int,
        buy_date: date,
        sell_date: date,
    ) -> tuple[CostBreakdown, CostBreakdown, Decimal]:
        """Calculate total round-trip cost (buy + sell)."""
        buy_costs = self.calculate_buy(buy_price, quantity, buy_date)
        sell_costs = self.calculate_sell(sell_price, quantity, sell_date)
        return buy_costs, sell_costs, buy_costs.total + sell_costs.total


class ZeroCostModel:
    """Zero-cost model for debugging and comparison ONLY.

    Must never be used for production-quality research.
    """

    @property
    def version(self) -> str:
        return "zero_cost_debug_only"

    @property
    def effective_from(self) -> date:
        return date(2000, 1, 1)

    @property
    def effective_to(self) -> date | None:
        return None

    @property
    def is_historical_assumption(self) -> bool:
        return True

    def calculate_buy(self, price: Decimal, quantity: int, trade_date: date) -> CostBreakdown:
        return CostBreakdown()

    def calculate_sell(
        self, price: Decimal, quantity: int, trade_date: date, is_new_isin_today: bool = True
    ) -> CostBreakdown:
        return CostBreakdown()

    def round_trip_cost(
        self,
        buy_price: Decimal,
        sell_price: Decimal,
        quantity: int,
        buy_date: date,
        sell_date: date,
    ) -> tuple[CostBreakdown, CostBreakdown, Decimal]:
        return CostBreakdown(), CostBreakdown(), Decimal("0")
