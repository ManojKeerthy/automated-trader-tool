"""Auditable trade ledger for backtesting.

Persists every executed trade with full entry/exit provenance, fees breakdown,
slippage impact, and holding period details.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.costs import CostBreakdown


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
    fees_breakdown: dict[str, str] = field(default_factory=dict)
    metadata_json: dict[str, Any] = field(default_factory=dict)


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
    ) -> TradeRecord:
        """Create and store a trade audit record."""
        if not (signal_date < entry_date <= exit_date):
            raise ValueError(
                f"Temporal invariant violation for {symbol}: signal_date ({signal_date}) < "
                f"entry_date ({entry_date}) <= exit_date ({exit_date}) is required."
            )

        gross_pnl = (exit_price - entry_price) * quantity
        total_fees = entry_costs.total + exit_costs.total
        net_pnl = gross_pnl - total_fees
        holding_days = (exit_date - entry_date).days

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
            fees_breakdown=combined_fees.to_dict(),
            metadata_json={
                "entry_costs": entry_costs.to_dict(),
                "exit_costs": exit_costs.to_dict(),
            },
        )
        self.trades.append(record)
        return record

    def __len__(self) -> int:
        return len(self.trades)
