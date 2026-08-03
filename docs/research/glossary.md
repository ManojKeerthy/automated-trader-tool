# TRADECRAFT RESEARCH GLOSSARY

> **CANONICAL TERMINOLOGY SPECIFICATION**: Authoritative definitions of all quantitative research, backtesting, and governance terms.

---

### DEVELOPMENT DATASET
The primary historical dataset (`2016-08-01` $\rightarrow$ `2021-12-31`) used for pre-registered hypothesis testing and Development Gate evaluation.

### VALIDATION DATASET
The secondary historical dataset (`2022-01-01` $\rightarrow$ `2024-06-30`), strictly sealed during Development, used ONLY for single out-of-sample validation of Development survivors.

### FINAL TEST DATASET
The tertiary historical dataset (`2024-07-01` $\rightarrow$ `2026-07-28`), strictly sealed, reserved for final pre-production validation.

### POINT-IN-TIME (PIT)
A data query property ensuring that at historical date $T$, the system sees only data that was available at date $T$, preventing lookahead and survivorship bias.

### LOOK-AHEAD BIAS
The fatal flaw of using future price, volume, or corporate action data that was unknown at the time of signal generation.

### SURVIVORSHIP BIAS
The distortion caused by selecting historical universe constituents based on current index membership, ignoring past delistings and removals.

### SIGNAL INTENT
An abstract strategy output representing a desired trade action (direction, order type, stop loss level) generated at Date $T$ close.

### ORDER INTENT
A sized order specification ready for execution simulator submission, incorporating capital allocation and whole-share calculations.

### FILL / EXECUTION
The realized transaction matching an Order Intent, executed strictly at Date $T+1$ open or later with explicit costs and slippage.

### COMPLETED TRADE
A closed position pair (entry fill + exit fill) with fully reconciled gross P&L, explicit costs, and net P&L.

### R-MULTIPLE
The ratio of net P&L to initial trade risk:  
$$R = \frac{\text{Net PnL}}{\text{Quantity} \times (\text{Entry Price} - \text{Stop Loss Level})}$$

### EXPECTANCY (R)
The expected average R-multiple gain per trade across all completed trades in a backtest run.

### PROFIT FACTOR
The ratio of total gross profit from winning trades to total gross loss from losing trades:  
$$\text{Profit Factor} = \frac{\sum \text{Net PnL of Winning Trades}}{\left| \sum \text{Net PnL of Losing Trades} \right|}$$

### GROSS EDGE
The strategy P&L generated prior to deducting transaction costs and execution slippage.

### NET EDGE
The strategy P&L remaining after deducting all explicit transaction costs and execution slippage.

### RESEARCH GRAVEYARD
The permanent, immutable repository of abandoned strategy families that failed Development research gates.

### STRATEGY LINEAGE
The chronological history of strategy versions (e.g. V1 $\rightarrow$ V2 $\rightarrow$ V3) sharing a core economic hypothesis.

### DEVELOPMENT SURVIVOR
A strategy version that passes all pre-declared criteria of `V2DevelopmentGate v1.0` on Development data, making it `ELIGIBLE_FOR_FUTURE_VALIDATION`.
