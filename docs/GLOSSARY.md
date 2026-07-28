# TradeCraft — Glossary

> Version: 1.0.0 | Last Updated: 2026-07-28
>
> All financial and trading terms used in the platform, explained for beginners.

## A

**Alpha** — The excess return of a strategy compared to a benchmark (like the Nifty 50). Positive alpha means the strategy outperformed the benchmark after accounting for risk.

**ATR (Average True Range)** — Measures how much a stock typically moves in a day, accounting for gaps. Used for setting stop-losses at a distance that respects the stock's normal volatility. A stock with ATR of ₹50 moves about ₹50/day on average.

**ADX (Average Directional Index)** — Measures the strength of a trend (not its direction). Above 25 suggests a strong trend; below 20 suggests no clear trend.

## B

**Backtest** — Simulating a trading strategy on historical data to see how it would have performed. Not a guarantee of future performance, but helps identify obviously bad strategies.

**Beta** — How much a stock moves relative to the market. Beta of 1.0 means it moves roughly with the market. Beta of 1.5 means it tends to move 50% more than the market.

**Bollinger Bands** — Bands placed above and below a moving average, typically at 2 standard deviations. When price touches the upper band, the stock may be "stretched." When it touches the lower band, it may be oversold.

**Breakout** — When price moves above a resistance level or below a support level with conviction, potentially starting a new trend.

## C

**CAGR (Compound Annual Growth Rate)** — The annualised rate of return, accounting for compounding. If ₹50,000 grows to ₹65,000 over 2 years, the CAGR is about 14%.

**Calmar Ratio** — Annual return divided by maximum drawdown. Higher is better. A Calmar of 2.0 means the strategy earned twice its worst drawdown per year.

**Circuit Breaker** — A market-wide or stock-specific trading halt triggered when prices move too much too fast. Designed to prevent panic.

**CVaR (Conditional Value at Risk)** — The expected loss in the worst scenarios (beyond VaR). If the 5% VaR is ₹2,500, the CVaR tells you the average loss when things go worse than that.

## D

**Donchian Channel** — The highest high and lowest low over a fixed number of days. A breakout above the upper channel may signal a new uptrend.

**Drawdown** — The decline from a peak value. If your portfolio went from ₹55,000 (peak) to ₹49,500, that's a ₹5,500 or 10% drawdown.

## E

**Expectancy** — The average amount you expect to win (or lose) per trade. Calculated as: (win rate × average win) – (loss rate × average loss). Positive expectancy means the strategy is expected to make money over many trades.

**Exposure** — The percentage of time the strategy has capital invested in the market. 50% exposure means half the time the strategy is in cash.

## G

**Gap** — When a stock opens significantly higher or lower than the previous close, creating a "gap" on the chart. Common after earnings or major news.

## I

**ISIN** — International Securities Identification Number. A unique 12-character code identifying a security globally.

## K

**Kill Switch** — An emergency control that immediately stops all trading activity, cancels pending orders, and optionally closes positions. The "big red button."

## L

**Liquidity** — How easily a stock can be bought or sold without significantly affecting its price. Nifty 50 stocks are generally highly liquid.

## M

**MACD (Moving Average Convergence Divergence)** — Shows the relationship between two moving averages. When the MACD line crosses above the signal line, it may indicate upward momentum.

**Market Breadth** — How many stocks are participating in a market move. If the index is up but most stocks are down, breadth is poor — the rally may be fragile.

**Market Regime** — The overall character of the market at a given time: bullish (rising), bearish (falling), sideways (range-bound), high volatility, low volatility.

**Maximum Drawdown** — The largest peak-to-trough decline during a specific period. The worst-case historical decline.

**Moving Average** — The average price over a specific number of days. A 50-day moving average smooths out daily noise to show the trend.

## N

**Nifty 50** — An index of the 50 largest and most liquid stocks on the National Stock Exchange of India. Our initial trading universe.

## O

**OHLCV** — Open, High, Low, Close, Volume — the five key data points for each trading day (or candle).

## P

**Paper Trading** — Simulated trading with fake money. All the mechanics of real trading without risking real capital. Used to validate strategies.

**Payoff Ratio** — Average winning trade divided by average losing trade. A ratio of 2.0 means wins are on average twice as large as losses.

**Profit Factor** — Total gross profit divided by total gross loss. Above 1.0 means the strategy is profitable overall. Above 2.0 is considered good.

**Pullback** — A temporary decline within an ongoing uptrend. Some strategies buy during pullbacks, expecting the uptrend to resume.

## R

**Recovery Factor** — Total net profit divided by maximum drawdown. Higher means the strategy recovers from drawdowns more effectively.

**Relative Strength** — How a stock performs compared to the market or its sector. A stock with strong relative strength outperforms its peers.

**Resistance** — A price level where a stock has historically faced selling pressure and turned lower. Like a ceiling.

**Risk/Reward Ratio** — The ratio of potential loss (to stop) versus potential gain (to target). A 1:3 ratio means risking ₹1 to potentially gain ₹3.

**Risk Lock** — A system state that blocks all new position entries when portfolio drawdown exceeds the critical threshold (10%). Requires human review to clear.

**RSI (Relative Strength Index)** — Measures speed and magnitude of price changes on a 0–100 scale. Above 70 is "overbought" (possibly due for a decline), below 30 is "oversold" (possibly due for a bounce).

## S

**SEBI** — Securities and Exchange Board of India. The primary regulator of securities markets in India.

**Sharpe Ratio** — Measures return per unit of risk (volatility). Higher is better. A Sharpe of 1.0 means the strategy earned 1 unit of return for each unit of risk taken. Above 1.0 is generally considered good.

**Slippage** — The difference between the expected trade price and the actual fill price. In liquid stocks, slippage is usually small.

**Sortino Ratio** — Like the Sharpe ratio but only counts downside volatility as "risk." Often considered more relevant since upside volatility is desirable.

**STT (Securities Transaction Tax)** — Tax charged on securities transactions in India. Currently 0.1% on delivery trades (buy + sell combined).

**Stop Loss** — A predetermined price at which a losing position will be sold to limit further losses. A safety net that defines the maximum acceptable loss on a trade.

**Support** — A price level where a stock has historically found buying interest and bounced higher. Like a floor.

**Survivorship Bias** — The error of only looking at stocks that survived to today, ignoring those that were delisted or went bankrupt. Makes historical strategies look better than they actually were.

**Swing Trading** — A trading style that holds positions for days to weeks (sometimes months), capturing "swings" in price. Not day trading (same day) or investing (years).

## T

**Turnover** — How frequently the portfolio's holdings change. High turnover means frequent trading, which increases transaction costs.

## V

**VaR (Value at Risk)** — The maximum loss expected over a given period at a given confidence level. "The 95% daily VaR is ₹1,000" means there's a 95% chance the daily loss won't exceed ₹1,000.

**Volatility** — How much a stock's price fluctuates. Higher volatility means bigger price swings — more opportunity but also more risk.

## W

**Walk-Forward Analysis** — A validation technique where you optimise a strategy on one period, test it on the next, then roll forward. Tests whether the strategy adapts to changing markets.

**Win Rate** — The percentage of trades that are profitable. A 50% win rate with a 2:1 payoff ratio is a good system — you don't need to be right most of the time if your winners are bigger than your losers.
