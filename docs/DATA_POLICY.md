# TradeCraft — Data Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Data Philosophy

Never silently use low-quality data. Every dataset must have documented provenance, and data quality must be validated before use in trading decisions.

## 2. Dataset Documentation

Every dataset used by the system must document:

| Field | Description |
|-------|-------------|
| `provider` | Source of the data |
| `licence` | Usage constraints and terms |
| `update_frequency` | How often data is refreshed |
| `timezone` | Timezone of timestamps |
| `adjustment_methodology` | How corporate actions are handled |
| `known_limitations` | Known quality issues |
| `cost` | Free or paid (amount) |
| `point_in_time` | Whether data is point-in-time correct |

## 3. Market Data

### Primary Source: Zerodha Kite Connect Historical API

- **Data type**: Daily OHLCV candles
- **Provider**: Zerodha (via Kite Connect API)
- **Cost**: Requires Kite Connect API subscription (user-approved)
- **Timezone**: IST (Asia/Kolkata)
- **Storage**: PostgreSQL (local)
- **Priority**: DAILY OHLCV for V1 swing strategies

Intraday data will only be introduced when a strategy demonstrates a specific requirement for it.

### Provider Interface

```
MarketDataProvider (interface)
├── ZerodhaMarketDataProvider  — Kite Connect historical candle API
├── TestMarketDataProvider     — Fixture-based for testing
└── FuturePaidProvider         — If Zerodha data proves inadequate
```

Market data consumers (strategies, backtester) depend on the interface, never on a specific provider.

### Data Quality Checks

Before trusting data for research or trading:

| Check | Description |
|-------|-------------|
| Missing sessions | Compare against trading calendar, flag missing dates |
| Duplicates | No duplicate OHLCV records per instrument per date |
| Impossible OHLC | Verify: low ≤ open ≤ high, low ≤ close ≤ high |
| Zero/invalid volume | Flag zero or negative volume |
| Timezone consistency | All timestamps in expected timezone |
| Unexpected gaps | Flag gaps not explained by holidays/weekends |
| Corporate actions | Cross-reference with known corporate action dates |
| Extreme returns | Flag returns > ±20% (configurable) for review |
| Incomplete downloads | Verify expected date range coverage |

### Raw vs Adjusted Data

- Store **raw** market observations (unadjusted OHLCV)
- Derive **adjusted** series separately for research use
- Every adjustment is traceable to a specific corporate action
- Both raw and adjusted series are available in the database

## 4. Corporate Actions Data

### Primary Source: NSE

```
CorporateActionsProvider (interface)
├── NSECorporateActionsProvider  — Official NSE data
├── TestCorporateActionsProvider — Fixture-based
└── FuturePaidProvider           — If free sources insufficient
```

### Modelled Actions
- Stock splits
- Bonuses
- Dividends (cash)
- Rights issues
- Mergers / demergers (where relevant)
- Symbol changes
- Delistings

### Quality Rules
- Never fabricate missing corporate actions
- If reliable historical coverage cannot be obtained, STOP before trusting affected backtests
- Propose paid dataset for user approval if needed

## 5. Trading Calendar

### Architecture

```
Official NSE/BSE information (authoritative truth)
  ▼
Calendar ingestion / verification
  ▼
Internal TradingCalendar abstraction
  ▼
Strategies / Backtester / Scheduler
```

### Implementation
- Use `exchange_calendars` (or equivalent) Python library as convenient implementation
- **Validate** library dates against official exchange information
- The Python library is NOT regulatory truth
- Persist calendar used for historical simulations (reproducibility)

### Supported Calendar Features
- Normal trading days
- Exchange holidays
- Special sessions
- Muhurat trading
- Unexpected exchange closures
- Mid-year changes

### Quality Check
- Automated detection of disagreement between stored calendar and authoritative exchange information
- NSE is primary calendar for initial Nifty 50 trading
- BSE calendar support exists architecturally but does not block initial functionality

## 6. Timezone Handling

| Rule | Implementation |
|------|---------------|
| Storage | UTC for all timestamps |
| Market logic | Explicit `Asia/Kolkata` |
| Display | `Asia/Kolkata` for dashboard |
| Never | Rely on computer's local timezone |
| Trading calendar | `Asia/Kolkata` for session boundaries |

The application must behave correctly when executed from any timezone.

## 7. Paid Data Policy

- Do NOT purchase paid data services without explicit user approval
- Document evidence if free data is inadequate
- Propose specific provider with cost/benefit analysis
- Any new paid service requires user approval
