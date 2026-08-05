# M3R — EXECUTION-DERIVED RESEARCH PIPELINE ARCHITECTURE

> **PIPELINE STATUS**: **`EXECUTION_DERIVED_PRODUCTION`**  
> **AUTOMATED AUTHENTICITY VERIFIER**: `src/tradecraft/research/authenticity_verifier.py` (Passing 100%)  
> **ARCHITECTURAL DECISION RECORD**: [ADR-020](file:///c:/infiligence/automated-trader-tool/docs/research/adr/ADR-020_EXECUTION_DERIVED_RESEARCH.md)

---

## 1. SINGLE AUTHORITATIVE RESEARCH DATA FLOW

Every research runner script in TradeCraft is strictly constrained to the following single-chain execution pipeline:

```
                  [ Historical Database (tradecraft.db) ]
                                    ↓
                         [ DataPortal Layer ]
                                    ↓
                [ BacktestEngine.run(BacktestConfig) ]
                                    ↓
                        [ BacktestResult Object ]
                                    ↓
         ┌──────────────────────────┴──────────────────────────┐
         ↓                                                     ↓
 [ Trade Ledger (res.trades) ]                 [ Equity Curve (res.equity_curve) ]
         ↓                                                     ↓
 [ Performance Metrics (PF, Sharpe, R) ] ──────────────┤
                                                       ↓
                                     [ Execution-Derived Reports & JSON ]
```

---

## 2. PROHIBITION RULES & AUTOMATED ENFORCEMENT

1. **Synthetic Market Bar Injection**: PROHIBITED. All prices must originate from SQL queries on the `market_bars` database table.
2. **Hard-Coded Metrics**: PROHIBITED. Literals assigned to metric variables (`profit_factor = 2.50`) raise fatal static analysis errors in `AuthenticityVerifier`.
3. **Synthesized Trade Ledgers**: PROHIBITED. `random.seed()`, `random.uniform()`, and loop-synthesized trades are blocked.
4. **Automated CI Enforcement**: `AuthenticityVerifier` runs automatically in CI/CD before any backtest execution.

---

## 3. DATA LINEAGE MAP FOR RESEARCH OUTPUTS

| Reported Research Metric | Single Authoritative Execution Source | Python Attribute |
| :--- | :--- | :--- |
| **Gross Profit / Loss** | Summed from executed trades | `BacktestResult.trades[i].net_pnl` |
| **Profit Factor** | Ratio of gross profits to gross losses | `gross_profit / gross_loss` |
| **Expectancy ($R$)** | Average win/loss ratio in R-multiples | `(avg_win - avg_loss) / avg_loss` |
| **Maximum Drawdown (%)** | Peak-to-trough drop in total equity | `BacktestResult.max_drawdown_pct` |
| **Sharpe Ratio** | Risk-normalized excess return | `BacktestResult.sharpe_ratio` |
| **Double-Entry Residual Error** | Cash balance diff vs realized P&L | `abs(final_equity - initial_capital - net_pnl)` |
