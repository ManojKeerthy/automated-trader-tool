# TradeCraft — News Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. News Philosophy

News and events are **information inputs**, not trade triggers. The system may consume news, but news must NEVER automatically trigger trades simply because an LLM labels it "bullish" or "bearish."

## 2. Source Requirements

- News sources must have documented **provenance** (origin, publisher, timestamp)
- Prefer **primary sources** for corporate and regulatory events (exchange filings, SEBI circulars, company announcements)
- Secondary/aggregated news is supplementary context, not authoritative
- Store source metadata alongside news content

## 3. News-Derived Signals

- News-derived signals must be **researched and validated** like any other trading signal
- They go through the full strategy lifecycle (IDEA → RESEARCH → ... → PRODUCTION)
- LLM sentiment labels are NOT validated signals
- Statistical validation is required before any news-based feature enters a strategy

## 4. Event Awareness

The system should be aware of scheduled events where appropriate:

| Event Type | Source | Use |
|------------|--------|-----|
| Earnings dates | Exchange filings | Risk consideration for holding positions |
| Corporate action ex-dates | NSE | Price adjustment, position impact |
| SEBI/regulatory announcements | SEBI website | Compliance impact |
| Macro events (RBI policy, etc.) | Official calendars | Market regime context |
| Index rebalancing | NSE | Universe changes |

## 5. What News Does NOT Do

- Does not automatically generate buy/sell orders
- Does not override risk controls
- Does not bypass the human approval workflow
- Does not serve as the sole basis for a trade
