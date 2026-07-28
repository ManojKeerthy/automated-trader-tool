# TradeCraft — UI/UX Design

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Dashboard Overview

The web dashboard is the primary human interface. It serves two critical functions:
1. **Monitoring** — Portfolio, risk, compliance, system health
2. **Approval** — Trade proposals requiring human decision

Technology: React + TypeScript (implemented in M8).

## 2. Target Audience

The user is an experienced developer but a beginner in quantitative finance. The UI must:
- Explain financial terminology contextually
- Present trade proposals in plain language
- Make risk visible and understandable
- Never assume the user knows what "Sharpe ratio" or "ATR" means

## 3. Required Dashboard Views

### Portfolio Overview
| Element | Description |
|---------|-------------|
| Portfolio value | Total current value (cash + invested) |
| Cash | Available cash |
| Invested capital | Capital in open positions |
| Realised P&L | Profit/loss from closed trades |
| Unrealised P&L | Paper profit/loss on open positions |
| Drawdown | Current drawdown from peak |
| Open portfolio risk | Total risk across open positions |

### Trade Proposals
| Element | Description |
|---------|-------------|
| Instrument | Stock name and symbol |
| Strategy | Which strategy generated the signal |
| Setup description | Plain-language explanation of why |
| Entry price | Proposed entry price |
| Stop loss | Protective stop price |
| Target / exit method | How exit is determined |
| Quantity | Number of shares |
| Capital required | Total cost |
| Capital at risk | Maximum possible loss |
| Risk/reward | Ratio where applicable |
| Portfolio impact | How this changes portfolio allocation |
| Market regime | Current market context |
| Sector context | Sector analysis |
| News/events | Relevant recent events |
| Risks | What could go wrong |
| APPROVE / REJECT buttons | User action |

### Open Positions
| Element | Description |
|---------|-------------|
| Per-position details | Entry, current, stop, target, P&L, strategy |
| Exit request | Button to request exit (goes through approval) |

### System Status
| Element | Description |
|---------|-------------|
| Paper/Live indicator | Prominently displayed mode |
| RISK LOCK status | Normal / Elevated / Risk Lock |
| KILL SWITCH | Emergency button, always accessible |
| Strategy health | Per-strategy status |
| Market regime | Current detection |
| Compliance status | Green / Yellow / Red |
| Data freshness | Last update timestamps |
| System health | Component health checks |

## 4. Terminology Tooltips

Critical financial terms must have contextual explanations via ⓘ icons:

| Term | Tooltip Example |
|------|----------------|
| Sharpe Ratio ⓘ | "Measures return relative to risk. Higher is better. A ratio above 1.0 means returns are good compared to the volatility. Think of it as 'return per unit of pain.'" |
| Maximum Drawdown ⓘ | "The largest peak-to-trough decline in portfolio value. If your portfolio went from ₹55,000 to ₹49,500, that's a 10% drawdown." |
| ATR ⓘ | "Average True Range — measures how much a stock typically moves in a day. Used for setting stop-losses at a reasonable distance." |
| Risk/Reward ⓘ | "Ratio of potential loss to potential gain. A 1:3 ratio means you risk ₹1 to potentially make ₹3." |
| Stop Loss ⓘ | "A predetermined price where the position will be sold to limit losses. Like a safety net." |
| Support ⓘ | "A price level where a stock has historically found buying interest and bounced higher." |
| Resistance ⓘ | "A price level where a stock has historically faced selling pressure and turned lower." |
| RSI ⓘ | "Relative Strength Index — measures whether a stock is 'overbought' (possibly due for a pullback) or 'oversold' (possibly due for a bounce). Ranges from 0-100." |
| MACD ⓘ | "Moving Average Convergence Divergence — a momentum indicator that shows the relationship between two moving averages. Used to identify trend changes." |
| Relative Strength ⓘ | "How a stock is performing compared to the overall market or its sector. Strong relative strength means it's outperforming." |

Explanations must remain available permanently — not removed when the user becomes more experienced.

## 5. Design Principles

- **Clarity over density** — Prioritise readability over showing maximum data
- **Risk visibility** — Risk state should be immediately obvious (colour-coded)
- **Mode visibility** — PAPER/LIVE mode must be impossible to miss
- **Responsive** — Work on desktop browsers (Chrome, Edge, Safari, Firefox)
- **Accessible** — Reasonable colour contrast, readable font sizes
- **No OS coupling** — Dashboard works on any OS with a modern browser

## 6. Colour Coding

| Colour | Meaning |
|--------|---------|
| Green | Positive P&L, healthy status, normal risk |
| Red | Negative P&L, errors, risk warnings |
| Yellow/Amber | Warnings, elevated risk, stale data |
| Blue | Informational, neutral |
| Purple/distinct | RISK LOCK active |
