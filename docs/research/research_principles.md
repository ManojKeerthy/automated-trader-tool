# TRADECRAFT RESEARCH PRINCIPLES

> **STATUS**: IMMUTABLE RESEARCH GOVERNANCE SPECIFICATION  
> **SCOPE**: APPLIES TO ALL CURRENT AND FUTURE RESEARCH CYCLES

---

## 1. REALITY BEATS THEORY
Empirical evidence on realistic, point-in-time data with explicit friction dominates theoretical market assumptions and backtest optimism.

## 2. PRE-REGISTRATION BEFORE TESTING
Hypotheses, parameter origins, and SHA256 configuration hashes MUST be frozen and persisted before observing backtest performance metrics.

## 3. ONE HYPOTHESIS = ONE EXPERIMENT
Each research iteration tests exactly one pre-registered structural hypothesis. Sweeps, grid searches, and trial-and-error retries are strictly prohibited.

## 4. ENGINEERING CORRECTNESS PRECEDES STATISTICAL INTERPRETATION
Backtest metrics cannot be evaluated until data portal lookahead protection, execution pipeline integrity, and accounting reconciliation are verified.

## 5. VALIDATION IS INFORMATION, NOT ANOTHER DEVELOPMENT SET
Validation and Final Test datasets exist solely to evaluate out-of-sample survival. They are never used for parameter tuning, hypothesis selection, or feature engineering.

## 6. NEVER OPTIMIZE TO HISTORICAL LUCK
Strategy rules must derive from economic mechanisms or risk principles, not from selecting parameters that happened to perform well on historical noise.

## 7. PRESERVE FAILED IDEAS
Negative research results are valuable assets. Every failed strategy and rejected parameterization must be permanently preserved in the Research Graveyard.

## 8. EVERY EXPERIMENT TEACHES SOMETHING
Failure to pass a Development Gate is a successful research outcome if it reveals market structural realities or friction limitations.

## 9. NO POST-HOC STRATEGY RESCUE
When a strategy fails a predeclared gate threshold, it is abandoned. Gate thresholds are never retroactively lowered or reinterpreted to save a failing strategy.

## 10. FIXED-TRADE COUNTERFACTUAL FRICTION TESTING
Sensitivity to transaction costs and slippage must be evaluated on fixed trade execution paths without regenerating signals or altering portfolio execution.

## 11. POINT-IN-TIME DATA IS NON-NEGOTIABLE
No indicator, feature, universe lookup, or corporate action adjustment may utilize information unavailable at the exact clock date $T$.

## 12. T+1 EXECUTION TIMING INVARIANT
Signals generated at date $T$ close are strictly executed at date $T+1$ open or later. Intraday lookahead between signal bar close and entry price is impossible.

## 13. EXACT FINANCIAL CONSERVATION
All cash, position values, explicit costs, and trade P&L must satisfy exact double-entry accounting conservation identities ($\le ₹0.0001$ residual).

## 14. MATERIAL HYPOTHESIS DISTINCTION REQUIRED FOR RE-ENTRY
An abandoned strategy family cannot be revived by minor parameter tweaks. Re-entry requires a genuinely new economic hypothesis.

## 15. GOVERNANCE PROTECTS INTELLECTUAL CAPITAL
Systematic research governance prevents accidental self-deception, over-fitting, and wasted capital, ensuring long-term institutional scalability.
