"""Auditable trade ledger for backtesting.

Persists every executed trade with full entry/exit provenance, fees breakdown,
slippage impact, and holding period details.

R-MULTIPLE INTEGRITY (defects F2 / F2b, fixed 2026-08-06)
=========================================================
The R-multiple is now computed ONCE, at trade close, from `initial_risk_per_share`
captured at ENTRY — not reconstructed later from a stop level that may have been
trailed, cleared, or never recorded.

The previous implementation recomputed R in `metrics.py` as
`net_pnl / |entry_price - stop_loss_level|`, which failed two ways:

1. `engine.py` passed `stop_loss_level` on only ONE of its three `record_trade` call
   sites. Trades exiting via strategy signal or end-of-backtest force close arrived with
   `stop_loss_level = None` and were silently scored `R = 0.0`. Since no strategy emitted
   exits, every winner was force-closed — so every winner scored 0 and only losers scored
   real (negative) R. `expectancy_r` was arithmetically incapable of being positive, and it
   was the gate that terminated all four Cycle 1 strategy families.

2. The stop was anchored to the signal-day close while the fill was the T+1 open. On a gap
   open the denominator collapsed toward zero and R exploded (-40R was observed on a single
   trade; the reported mean was -101.85R on a strategy that returned +20%).

Trades whose risk distance is degenerate are now marked `DEGENERATE_RISK` and EXCLUDED from
the R distribution rather than being scored zero. Excluding is honest; scoring zero is a
silent lie that biases the mean toward the losers.

See docs/research/REPO_AUDIT_2026-08-06.md §2.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.costs import CostBreakdown

# A stop closer than this fraction of the entry price is not a real risk boundary for daily
# swing trading on NSE equities - it is an artifact of anchoring the stop to the prior close
# and filling at the next open. Such trades are excluded from R statistics, not scored 0.
MIN_RISK_FRACTION_OF_PRICE = Decimal("0.005")  # 0.5%

R_STATUS_OK = "OK"
R_STATUS_NO_STOP = "NO_STOP_RECORDED"
R_STATUS_DEGENERATE = "DEGENERATE_RISK"


@dataclass
class TradeRecord:
    """Complete auditable record of a closed simulated trade."""

    trade_id: uuid.UUID
    run_id: uuid.UUID
    instrument_id: uuid.UUID
    instrument_symbol: str
    strategy_name: str
    strategy_version: str
    direction: str  # 'BUY'
    signal_date: date
    entry_date: date
    entry_price: Decimal
    exit_date: date
    exit_price: Decimal
    quantity: int
    gross_pnl: Decimal
    total_fees: Decimal
    slippage_cost: Decimal
    net_pnl: Decimal
    holding_days: int
    exit_reason: str
    stop_loss_level: Decimal | None = None
    # Risk distance captured at ENTRY. Never derived from a trailed or cleared stop.
    initial_risk_per_share: Decimal | None = None
    # R-multiple computed once at close. None means "not measurable", never "zero".
    r_multiple: Decimal | None = None
    r_multiple_status: str = R_STATUS_NO_STOP
    fees_breakdown: dict[str, str] = field(default_factory=dict)
    metadata_json: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Derive the R-multiple for records built directly rather than via the ledger.

        The invariant belongs to the record, not only to `TradeLedger.record_trade`, so that
        a TradeRecord constructed in a test, a migration or an analysis script cannot end up
        with a silently missing R while still carrying a valid stop.
        """
        if self.r_multiple is not None:
            return

        risk = self.initial_risk_per_share
        if risk is None and self.stop_loss_level is not None:
            risk = abs(self.entry_price - self.stop_loss_level)

        r, status = TradeLedger._compute_r_multiple(
            net_pnl=self.net_pnl,
            entry_price=self.entry_price,
            quantity=self.quantity,
            risk_per_share=risk,
        )
        self.initial_risk_per_share = risk
        self.r_multiple = r
        self.r_multiple_status = status


class TradeLedger:
    """Records and maintains all closed trades during a backtest."""

    def __init__(self, run_id: uuid.UUID):
        self.run_id = run_id
        self.trades: list[TradeRecord] = []

    def record_trade(
        self,
        instrument_id: uuid.UUID,
        symbol: str,
        strategy_name: str,
        strategy_version: str,
        signal_date: date,
        entry_date: date,
        entry_price: Decimal,
        exit_date: date,
        exit_price: Decimal,
        quantity: int,
        entry_costs: CostBreakdown,
        exit_costs: CostBreakdown,
        slippage_cost: Decimal,
        exit_reason: str,
        stop_loss_level: Decimal | None = None,
        initial_risk_per_share: Decimal | None = None,
    ) -> TradeRecord:
        """Create and store a trade audit record.

        Args:
            stop_loss_level: The stop in force at ENTRY (not the trailed stop at exit).
            initial_risk_per_share: |entry_price - initial_stop| captured at entry. If not
                supplied it is derived from `stop_loss_level`, but callers should always
                pass it explicitly so that trailing stops cannot corrupt the R denominator.
        """
        if not (signal_date < entry_date <= exit_date):
            raise ValueError(
                f"Temporal invariant violation for {symbol}: signal_date ({signal_date}) < "
                f"entry_date ({entry_date}) <= exit_date ({exit_date}) is required."
            )

        gross_pnl = (exit_price - entry_price) * quantity
        total_fees = entry_costs.total + exit_costs.total
        net_pnl = gross_pnl - total_fees
        holding_days = (exit_date - entry_date).days

        risk_per_share = initial_risk_per_share
        if risk_per_share is None and stop_loss_level is not None:
            risk_per_share = abs(entry_price - stop_loss_level)

        r_multiple, r_status = self._compute_r_multiple(
            net_pnl=net_pnl,
            entry_price=entry_price,
            quantity=quantity,
            risk_per_share=risk_per_share,
        )

        combined_fees = CostBreakdown(
            brokerage=entry_costs.brokerage + exit_costs.brokerage,
            stt=entry_costs.stt + exit_costs.stt,
            exchange_charges=entry_costs.exchange_charges + exit_costs.exchange_charges,
            gst=entry_costs.gst + exit_costs.gst,
            sebi_fee=entry_costs.sebi_fee + exit_costs.sebi_fee,
            stamp_duty=entry_costs.stamp_duty + exit_costs.stamp_duty,
            dp_charges=entry_costs.dp_charges + exit_costs.dp_charges,
            total=total_fees,
        )

        record = TradeRecord(
            trade_id=uuid.uuid4(),
            run_id=self.run_id,
            instrument_id=instrument_id,
            instrument_symbol=symbol,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            direction="BUY",
            signal_date=signal_date,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            exit_price=exit_price,
            quantity=quantity,
            gross_pnl=gross_pnl,
            total_fees=total_fees,
            slippage_cost=slippage_cost,
            net_pnl=net_pnl,
            holding_days=holding_days,
            exit_reason=exit_reason,
            stop_loss_level=stop_loss_level,
            initial_risk_per_share=risk_per_share,
            r_multiple=r_multiple,
            r_multiple_status=r_status,
            fees_breakdown=combined_fees.to_dict(),
            metadata_json={
                "entry_costs": entry_costs.to_dict(),
                "exit_costs": exit_costs.to_dict(),
            },
        )
        self.trades.append(record)
        return record

    @staticmethod
    def _compute_r_multiple(
        net_pnl: Decimal,
        entry_price: Decimal,
        quantity: int,
        risk_per_share: Decimal | None,
    ) -> tuple[Decimal | None, str]:
        """Compute the R-multiple, or explain why it is not measurable.

        Returns (r_multiple, status). A None r_multiple means the trade is EXCLUDED from R
        statistics. It never means zero — conflating "unmeasurable" with "scored zero" is
        precisely the defect that made expectancy_r structurally negative.
        """
        if risk_per_share is None or risk_per_share <= Decimal("0"):
            return None, R_STATUS_NO_STOP

        if entry_price > Decimal("0"):
            floor = entry_price * MIN_RISK_FRACTION_OF_PRICE
            if risk_per_share < floor:
                return None, R_STATUS_DEGENERATE

        total_risk = risk_per_share * Decimal(str(quantity))
        if total_risk <= Decimal("0"):
            return None, R_STATUS_DEGENERATE

        return net_pnl / total_risk, R_STATUS_OK

    # ------------------------------------------------------------------ diagnostics

    def r_multiple_coverage(self) -> tuple[int, int, Decimal]:
        """Return (measurable, total, coverage_pct) for the R distribution.

        Low coverage means expectancy_r is computed on a biased subsample and must not be
        used as a decision gate.
        """
        total = len(self.trades)
        if total == 0:
            return 0, 0, Decimal("0")
        measurable = sum(1 for t in self.trades if t.r_multiple is not None)
        return measurable, total, (Decimal(measurable) / Decimal(total)) * Decimal("100")

    def exit_reason_breakdown(self) -> dict[str, int]:
        """Count trades by exit reason. Used to detect exits that never fire."""
        counts: dict[str, int] = {}
        for t in self.trades:
            counts[t.exit_reason] = counts.get(t.exit_reason, 0) + 1
        return counts

    def __len__(self) -> int:
        return len(self.trades)
