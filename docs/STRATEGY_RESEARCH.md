# TradeCraft — Strategy Research Methodology

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Research Philosophy

- Never assume a trading concept works because it is popular
- Every hypothesis must be tested against data
- Complexity must earn its place through demonstrable improvement
- Negative results are valuable — they prevent deploying broken strategies

## 2. Hypothesis-Driven Research

Every research effort must start with a clear hypothesis:

```
IF [condition/setup] occurs in [universe]
THEN [expected outcome] with [timeframe]
BECAUSE [plausible mechanism for edge]
```

The "because" is critical. A pattern without a plausible economic or behavioural mechanism is likely data mining.

## 3. Research Methodology

### Step 1: Hypothesis Formation
- Document the hypothesis
- Identify the proposed edge mechanism
- Define measurable success criteria

### Step 2: Data Preparation
- Ensure data quality (see DATA_POLICY.md)
- Apply point-in-time universe (no survivorship bias)
- Handle corporate actions correctly
- Split data into: training / validation / out-of-sample

### Step 3: Feature Analysis
- Analyse candidate features individually before combining
- Check for statistical significance of predictive power
- Remove highly correlated features (reduce multicollinearity)
- Document feature rationale

### Step 4: Strategy Development
- Start simple — add complexity only when justified
- Use parameter ranges, not single optimised values
- Ensure rules are clear enough for deterministic implementation

### Step 5: In-Sample Backtest
- Full historical simulation (see BACKTESTING_POLICY.md)
- Include realistic transaction costs and slippage
- Use point-in-time data

### Step 6: Statistical Validation
- Assess whether results are statistically significant
- Check for sufficient trade count
- Verify across different market conditions

### Step 7: Out-of-Sample Testing
- Apply strategy to withheld data period
- Results must be consistent with in-sample (accounting for variance)

## 8. M3B.2 Revision Governance & Anti-Hallucination Rules

- **Dataset Terminology**: `2016-08-01` to `2021-12-31` is formally named `DEVELOPMENT` (consumed research data).
- **Out-of-Sample Firewalls**: `VALIDATION` (`2022-01-01` to `2024-06-30`) and `FINAL TEST` (`2024-07-01` to `2026-07-28`) are STRICTLY UNOBSERVED.
- **Blind Signal Viability**: Signal viability must be judged without calculating or exposing P&L / returns.
- **Predeclared Robustness**: Parameter perturbation neighbourhoods must be predeclared before P&L exposure. Robustness variants never replace frozen canonical V2.
- **Immutable Research Ledger**: All evaluated configurations, hashes, and lineages are recorded in `ImmutableResearchLedger`.

- Significant degradation invalidates the strategy

### Step 8: Walk-Forward Analysis
- Rolling window optimisation and testing
- Validates that the strategy adapts and remains robust

### Step 9: Robustness Testing
- Parameter sensitivity analysis (do nearby parameters produce similar results?)
- Regime dependence analysis
- Stress testing under adverse conditions
- Monte Carlo simulation where appropriate

### Step 10: Cost Analysis
- Realistic transaction costs
- Realistic slippage for the traded instruments
- Capacity analysis (is the strategy capacity appropriate for our capital?)

## 4. AI-Assisted Research

AI may assist at every research step but:
- AI-proposed strategies undergo the same validation
- AI-generated backtest code must be reviewed
- AI-claimed results must be independently verified
- AI cannot shortcut the lifecycle

## 5. Avoiding Overfitting

| Practice | Implementation |
|----------|---------------|
| Parameter count | Minimise free parameters |
| Parameter sensitivity | Nearby values must produce similar results |
| Data splits | Strict train/validate/test separation |
| Walk-forward | Rolling window validation |
| Trade count | Minimum trade count for statistical validity |
| Mechanism | Strategy must have plausible edge explanation |
| Out-of-sample | Hold out data not seen during development |
| Regime testing | Validate across bull, bear, and sideways markets |
