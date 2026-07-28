# TradeCraft — Strategy Governance

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Strategy Sources

TradeCraft supports two paths for strategy creation:

**A. Explicitly Implemented Systematic Strategies**
- Well-known, documented trading methodologies
- Implemented as code with clear, testable rules
- Example: Trend-following with moving average crossover + ATR-based stops

**B. AI-Assisted Strategy Research/Discovery**
- AI may formulate hypotheses and propose strategies
- AI-discovered strategies undergo the same validation as explicit strategies
- AI may NOT directly promote a strategy to production

## 2. Strategy Lifecycle

Every strategy must pass through this lifecycle. No stage may be skipped.

```
IDEA
  │  Hypothesis documented, rationale stated
  ▼
RESEARCH
  │  Data gathered, features explored, initial viability assessed
  ▼
BACKTEST
  │  Full historical simulation with transaction costs
  ▼
VALIDATION
  │  Statistical significance, metrics review
  ▼
OUT_OF_SAMPLE
  │  Tested on withheld data period
  ▼
WALK_FORWARD
  │  Rolling window validation
  ▼
ROBUSTNESS_TESTING
  │  Parameter sensitivity, regime dependence, stress testing
  ▼
COST_TESTING
  │  Realistic transaction costs, slippage, market impact
  ▼
PAPER_TRADING
  │  Live paper execution, real-time validation
  ▼
HUMAN_REVIEW
  │  Full review of all evidence by human
  ▼
APPROVED (Human Decision)
  │
  ▼
LIMITED_LIVE (small capital allocation)
  │
  ▼
PRODUCTION (full allocation)
```

Reverse transitions (demotion) are always permitted.

## 3. AI Permissions

### AI MAY:
- Formulate hypotheses
- Propose strategies, features, and parameters
- Run research and backtests
- Analyse failures
- Propose improvements
- Identify strategy degradation
- Research modifications to live strategies

### AI MAY NOT:
- Directly promote a strategy to production
- Silently alter production strategy behaviour
- Bypass the lifecycle
- Override human rejection

## 4. Strategy Versioning

All production strategy versions are **immutable**. Once a strategy version is in production:

- Its parameters cannot be changed
- Its logic cannot be modified
- A new version must be created for any change
- The new version must pass through the full lifecycle

Version format: `{strategy_name}-v{major}.{minor}.{patch}`

Example: `momentum-breakout-v1.2.0`

## 5. Strategy Registry

The strategy registry maintains:
- All known strategies and their versions
- Current lifecycle stage of each version
- Promotion/demotion history
- Performance metrics per version
- Active/retired status

## 6. Candidate Features

These are **candidate information sources**, not mandatory rules:

| Category | Examples |
|----------|----------|
| Trend | Moving averages, trend lines, higher highs/lows |
| Momentum | RSI, MACD, rate of change |
| Breakout | Donchian channels, range breakouts |
| Volatility | ATR, Bollinger Bands, historical volatility |
| Volume | Volume profile, OBV, volume confirmation |
| Relative | Relative strength vs index, sector strength |
| Breadth | Market breadth indicators, advance/decline |
| Fundamental | PE, ROE, earnings growth, debt ratios |
| Event | Earnings dates, corporate actions, macro calendar |

Every feature must **justify itself empirically**. Do not create indicator soup. Complexity must earn its place.

## 7. Strategy Documentation Requirements

Each strategy must have a decision record documenting:
- Hypothesis and rationale
- Features used and why
- Entry rules
- Exit rules (protective and discretionary)
- Position sizing approach
- Universe requirements
- Backtest results with full metrics
- Out-of-sample results
- Walk-forward results
- Known limitations
- Failure modes
- Regime dependence
- Degradation monitoring plan
