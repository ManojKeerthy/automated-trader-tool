# ENGINEERING & ACCOUNTING LESSONS REGISTRY

> **TECHNICAL DEFECT RECONCILIATION**: Detailed documentation of the 6 major engineering, pipeline, and accounting defects discovered and resolved during Research Cycle 1.

---

## 1. SIGNAL-TO-EXECUTION SIZING DEFECT (M3B.2.1)
- **Symptom**: 32,822 confirmed strategy signals generated during M3B backtests yielded 0 executed trades.
- **Root Cause**: `SignalIntent.quantity_hint = None` propagated uncalibrated into `OrderIntent`. The execution simulator interpreted missing quantity as `0`, rejecting all orders without raising errors.
- **Resolution**: Wired `ResearchSizingCalculator` at the lifecycle boundary to convert unsized `SignalIntent` instances into whole-share `OrderIntent` quantities based on 10% equity cash-allocation.
- **Permanent Invariant**: All signals entering the execution simulator must possess explicit, non-zero whole-share quantities (`quantity >= 1`). Signal attrition counters must log:  
  $$\text{CONFIRMED\_SIGNALS} \equiv \sum \text{TERMINAL\_OUTCOMES}$$

---

## 2. ENTRY-COST ACCOUNTING DEFECT (M3B.2.2.1)
- **Symptom**: Backtest equity curve changes disagreed with completed trade ledger P&L, creating an accounting residual ($\approx ₹53.4\text{k}$ mismatch).
- **Root Cause**: Buy-side STT and transaction charges were deducted from `Portfolio.cash` upon entry fill, but were omitted from `TradeRecord.total_fees` and `TradeRecord.net_pnl` upon position exit.
- **Resolution**: Updated `TradeLedger` to accumulate both entry-side and exit-side transaction charges into `TradeRecord.total_fees` and compute `net_pnl = gross_pnl - total_fees`.
- **Permanent Invariant**: Exact accounting conservation identity:  
  $$\text{Final Equity} - \text{Initial Capital} \equiv \sum \text{TradeRecord.net\_pnl} \quad (\le ₹0.0001 \text{ residual})$$

---

## 3. POSITION METADATA OVERWRITE / TEMPORAL DEFECT (M3B.2.2.1)
- **Symptom**: 12 completed trades in early runs exhibited `signal_date == entry_date` or `entry_date > exit_date`.
- **Root Cause**: Instrument-keyed signal metadata dictionaries in `BacktestEngine` were overwritten when a new signal occurred for an instrument while an existing position was pending entry.
- **Resolution**: Keyed pending order metadata by unique `order_id` rather than `instrument_symbol`.
- **Permanent Invariant**: Every completed trade must strictly satisfy:  
  $$\text{signal\_date} < \text{entry\_date} \le \text{exit\_date}$$

---

## 4. END-OF-BACKTEST BOUNDARY MISMATCH (M3B.2.2.2)
- **Symptom**: Comparing strategies with open positions on the final session caused P&L discrepancies depending on whether open positions were ignored or marked to market.
- **Root Cause**: Unrealized paper P&L on open positions does not embed exit transaction fees or slippage, distorting trade-level metric calculations.
- **Resolution**: Formalised `EndOfBacktestPolicy.FORCE_CLOSE` as the mandatory research policy, explicitly liquidating all open positions on the final simulation date with full exit costs.
- **Permanent Invariant**: `final_snapshot.open_positions == 0` for all comparative research runs.

---

## 5. R-MULTIPLE DENOMINATOR SENSITIVITY (M3B.2.2)
- **Symptom**: Trend Pullback trade ledger reported extreme Min R of $-1627.00R$.
- **Root Cause**: Stop loss was placed ₹0.10 below entry price on a ₹500 stock. Initial risk per share was ₹0.10 (total risk ₹20.00 on 200 shares). A small exit loss of -₹162.70 divided by tiny ₹20.00 risk yielded $-8.135R$, while early uncalibrated R calculations used per-share stop distances directly.
- **Resolution**: Corrected R-multiple calculation to use total trade risk ($\text{risk\_per\_share} \times \text{quantity}$).
- **Permanent Invariant**: Risk denominator must equal actual initial capital risk. Stop loss levels placed unrealistically close to entry price are flagged as malformed.

---

## 6. SLIPPAGE ACCOUNTING CONVENTION (M3B.2.2.2)
- **Symptom**: Confusion regarding whether slippage should be deducted from trade net P&L as a separate fee line item.
- **Root Cause**: Double-counting slippage when execution price already embeds basis point slippage.
- **Resolution**: Established canonical rule: Fixed basis point slippage is directly applied to adjust execution fill prices (`entry_fill = entry_price * (1 + bps)`, `exit_fill = exit_price * (1 - bps)`). Gross P&L calculated from fill prices already embeds slippage.
- **Permanent Invariant**: Execution price Gross P&L embeds slippage. Explicit fees (STT, DP charges) are deducted from Gross P&L to yield Net P&L. Slippage is NEVER double-counted.
