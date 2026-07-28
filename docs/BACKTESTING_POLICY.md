# TradeCraft — Backtesting Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Purpose

Backtesting simulates how a strategy would have performed on historical data. Its purpose is to **assess whether a strategy has historically demonstrated an edge** — not to prove future profitability.

## 2. Bias Defenses

Every backtest must explicitly defend against:

| Bias | Defense |
|------|---------|
| **Look-ahead bias** | No data from time `t+1` may be used at time `t`. All indicators, screens, and decisions use only data available at the decision point. |
| **Survivorship bias** | Use point-in-time universe composition. Stocks that were delisted, removed from index, or went bankrupt must be included in the historical universe. |
| **Selection bias** | Do not cherry-pick the best-performing strategy variant. Report all tested variants. |
| **Data leakage** | Strict separation between training, validation, and test data. No parameter tuning on out-of-sample data. |
| **Overfitting** | Walk-forward validation, parameter sensitivity analysis, minimum trade counts. |
| **Parameter mining** | Test robustness across parameter ranges, not single optimal values. |
| **Unrealistic fills** | Model fills conservatively. Do not assume fills at exact signal price. |
| **Ignored costs** | Include brokerage, STT, GST, stamp duty, exchange fees, SEBI turnover fee. Model slippage. |
| **Ignored taxes** | Track tax implications where applicable. |
| **Corporate-action errors** | Use properly adjusted price series. Verify adjustments against known corporate actions. |
| **Insufficient sample** | Require minimum trade count for statistical conclusions. |

## 3. Transaction Cost Model

For Indian cash equities (NSE), approximate costs per trade:

| Component | Rate (approximate) |
|-----------|--------------------|
| Zerodha brokerage | ₹0 (equity delivery) |
| STT (Securities Transaction Tax) | 0.1% on buy+sell (delivery) |
| Exchange transaction charges (NSE) | ~0.00297% |
| GST | 18% on brokerage + exchange charges |
| SEBI turnover fee | 0.0001% |
| Stamp duty | Varies by state, ~0.015% on buy |
| Slippage (estimated) | 0.05%–0.20% depending on liquidity |

These rates MUST be verified against current Zerodha and regulatory fee schedules before production use.

## 4. Validation Metrics

Do not judge strategies solely by total return or win rate. Consider metrics from this framework, using those that are statistically appropriate:

### Return Metrics
| Metric | What It Measures |
|--------|-----------------|
| CAGR | Compound annual growth rate |
| Annualised return | Return normalised to annual period |
| Total return | Absolute return over period |

### Risk Metrics
| Metric | What It Measures |
|--------|-----------------|
| Annualised volatility | Standard deviation of returns |
| Maximum drawdown | Largest peak-to-trough decline |
| Maximum drawdown duration | Longest recovery period |
| VaR (Value at Risk) | Maximum loss at confidence level |
| CVaR (Conditional VaR) | Expected loss beyond VaR |
| Tail loss | Worst outcomes |

### Risk-Adjusted Return Metrics
| Metric | What It Measures |
|--------|-----------------|
| Sharpe ratio | Return per unit of total risk (annualised) |
| Sortino ratio | Return per unit of downside risk |
| Calmar ratio | Return per unit of maximum drawdown |
| Recovery factor | Total return / maximum drawdown |

### Trade-Level Metrics
| Metric | What It Measures |
|--------|-----------------|
| Win rate | Percentage of profitable trades |
| Average win | Mean profit on winning trades |
| Average loss | Mean loss on losing trades |
| Payoff ratio | Average win / average loss |
| Profit factor | Gross profit / gross loss |
| Expectancy | Expected profit per trade |
| Trade count | Total number of trades |

### System Metrics
| Metric | What It Measures |
|--------|-----------------|
| Exposure | Percentage of time invested |
| Turnover | Portfolio turnover rate |
| Transaction costs | Total cost impact |
| Alpha | Excess return vs benchmark |
| Beta | Sensitivity to benchmark |
| Benchmark comparison | Performance vs Nifty 50 TRI |

### Statistical Confidence
| Metric | What It Measures |
|--------|-----------------|
| Statistical significance | Whether results differ from random |
| Parameter sensitivity | How results change with parameter variation |
| Regime dependence | Performance across market regimes |

## 5. Minimum Requirements

Before a strategy can advance past BACKTEST stage:

- Minimum trade count: sufficient for statistical significance (generally ≥30 trades, more is better)
- Positive expectancy after all costs
- Sharpe ratio > 0.5 (guideline, not absolute threshold)
- Maximum drawdown within tolerance for the portfolio
- Consistent performance across out-of-sample data
- Walk-forward validation shows stability
- Parameter sensitivity shows robustness (no cliff effects)

These are guidelines. Context matters — a strategy with 25 high-quality trades may be acceptable if other evidence is strong.

## 6. Reproducibility

Every backtest must persist:
- Strategy version used
- Exact parameters
- Data snapshot reference (or data hash)
- Trading calendar used
- Universe composition at each point in time
- Transaction cost model used
- All results and metrics
- Timestamp of execution

This allows any backtest to be independently reproduced.
