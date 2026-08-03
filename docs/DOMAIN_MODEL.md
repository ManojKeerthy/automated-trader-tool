# TradeCraft — Domain Model

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────┐
│                     MARKET INTELLIGENCE                         │
│                                                                 │
│  Instrument  ·  Market Data  ·  Corporate Actions               │
│  Fundamentals  ·  News/Events  ·  Trading Calendar              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                     ANALYSIS & STRATEGY                         │
│                                                                 │
│  Feature Engineering  ·  Screening  ·  Market Regime            │
│  Strategy Engine  ·  Research  ·  Backtesting                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                     TRADING OPERATIONS                          │
│                                                                 │
│  Portfolio  ·  Risk  ·  Compliance                              │
│  Orders  ·  Positions  ·  P&L                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                     EXECUTION                                   │
│                                                                 │
│  Broker Abstraction  ·  Paper Broker  ·  Zerodha Adapter        │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Core Domain Entities

### Instrument
Represents a tradeable security.

| Attribute | Type | Description |
|-----------|------|-------------|
| `instrument_id` | UUID | Internal unique identifier |
| `symbol` | str | NSE trading symbol (e.g., "RELIANCE") |
| `isin` | str | ISIN code (e.g., "INE002A01018") |
| `name` | str | Full company name |
| `exchange` | Exchange | NSE or BSE |
| `sector` | str | GICS/industry sector |
| `industry` | str | Industry classification |
| `lot_size` | int | Minimum tradeable quantity |
| `tick_size` | Decimal | Minimum price increment |
| `is_active` | bool | Currently listed and tradeable |
| `nifty50_member_from` | date | None | Point-in-time membership |
| `nifty50_member_to` | date | None | Membership end (None if current) |

### OHLCV (Market Data Bar)

| Attribute | Type | Description |
|-----------|------|-------------|
| `instrument_id` | UUID | Foreign key to Instrument |
| `date` | date | Trading date |
| `open` | Decimal | Opening price |
| `high` | Decimal | Highest price |
| `low` | Decimal | Lowest price |
| `close` | Decimal | Closing price |
| `volume` | int | Traded volume |
| `provider` | str | Data source identifier |
| `is_adjusted` | bool | Whether corporate-action adjusted |
| `adjustment_factor` | Decimal | Cumulative adjustment factor |

### CorporateAction

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Unique identifier |
| `instrument_id` | UUID | Affected instrument |
| `action_type` | CorporateActionType | SPLIT, BONUS, DIVIDEND, etc. |
| `ex_date` | date | Ex-date |
| `record_date` | date | None | Record date |
| `ratio_from` | int | None | e.g., 1 in 1:2 split |
| `ratio_to` | int | None | e.g., 2 in 1:2 split |
| `amount` | Decimal | None | Dividend amount per share |
| `source` | str | Data source |
| `verified` | bool | Verified against official source |

### Strategy

| Attribute | Type | Description |
|-----------|------|-------------|
| `strategy_id` | UUID | Unique identifier |
| `name` | str | Human-readable name |
| `version` | str | Semantic version (immutable) |
| `description` | str | What the strategy does |
| `lifecycle_stage` | StrategyLifecycle | IDEA through PRODUCTION |
| `parameters` | dict | Strategy configuration |
| `created_at` | datetime | Creation timestamp (UTC) |
| `promoted_at` | datetime | None | When promoted to production |
| `promoted_by` | str | None | Who approved promotion |

### Signal

| Attribute | Type | Description |
|-----------|------|-------------|
| `signal_id` | UUID | Unique identifier |
| `strategy_id` | UUID | Generating strategy |
| `strategy_version` | str | Exact strategy version |
| `instrument_id` | UUID | Target instrument |
| `direction` | TradeSide | BUY |
| `entry_price` | Decimal | Proposed entry |
| `stop_loss` | Decimal | Protective stop |
| `target_price` | Decimal | None | Target (if applicable) |
| `exit_methodology` | str | How exit is determined |
| `quantity` | int | Proposed shares |
| `capital_required` | Decimal | Total capital needed |
| `capital_at_risk` | Decimal | Maximum loss if stopped |
| `risk_reward_ratio` | Decimal | None | R:R if target exists |
| `confidence` | Decimal | Strategy confidence score |
| `generated_at` | datetime | Signal time (UTC) |
| `valid_until` | datetime | None | Expiry time |
| `market_regime` | MarketRegime | Current regime |
| `technical_evidence` | dict | Supporting technical data |
| `fundamental_evidence` | dict | None | Supporting fundamentals |
| `rationale` | str | Why edge exists |
| `risks` | list[str] | Identified risks |

### TradeProposal

| Attribute | Type | Description |
|-----------|------|-------------|
| `proposal_id` | UUID | Unique identifier |
| `signal_id` | UUID | Originating signal |
| `status` | ProposalStatus | PENDING, APPROVED, REJECTED, EXPIRED |
| `portfolio_impact` | dict | How this affects portfolio |
| `sector_context` | str | Sector analysis |
| `news_context` | str | None | Relevant news |
| `created_at` | datetime | Proposal time (UTC) |
| `reviewed_at` | datetime | None | Review time |
| `reviewed_by` | str | None | Reviewer |
| `rejection_reason` | str | None | Why rejected |

### Order

| Attribute | Type | Description |
|-----------|------|-------------|
| `order_id` | UUID | Internal unique identifier |
| `broker_order_id` | str | None | Broker's order ID |
| `proposal_id` | UUID | Approved proposal |
| `instrument_id` | UUID | Target instrument |
| `side` | TradeSide | BUY |
| `order_type` | OrderType | MARKET, LIMIT, SL, SL-M |
| `quantity` | int | Shares |
| `price` | Decimal | None | Limit price |
| `trigger_price` | Decimal | None | Stop-loss trigger |
| `status` | OrderStatus | CREATED, SUBMITTED, FILLED, etc. |
| `filled_quantity` | int | Shares filled |
| `average_price` | Decimal | None | Fill price |
| `broker_mode` | BrokerMode | PAPER or LIVE |
| `created_at` | datetime | Order creation (UTC) |
| `submitted_at` | datetime | None | Submission time |
| `filled_at` | datetime | None | Fill time |
| `idempotency_key` | str | Duplicate prevention |

### Position

| Attribute | Type | Description |
|-----------|------|-------------|
| `position_id` | UUID | Unique identifier |
| `instrument_id` | UUID | Held instrument |
| `strategy_id` | UUID | Originating strategy |
| `entry_order_id` | UUID | Entry order |
| `quantity` | int | Shares held |
| `average_entry_price` | Decimal | Entry cost basis |
| `current_stop` | Decimal | Active stop-loss price |
| `current_target` | Decimal | None | Active target |
| `exit_methodology` | str | How exit is determined |
| `status` | PositionStatus | OPEN, CLOSED, PARTIALLY_CLOSED |
| `opened_at` | datetime | Position open time (UTC) |
| `closed_at` | datetime | None | Close time |
| `unrealised_pnl` | Decimal | Mark-to-market P&L |
| `realised_pnl` | Decimal | Closed P&L |

### Portfolio

| Attribute | Type | Description |
|-----------|------|-------------|
| `portfolio_id` | UUID | Unique identifier |
| `mode` | BrokerMode | PAPER or LIVE |
| `initial_capital` | Decimal | Starting capital (₹50,000) |
| `cash` | Decimal | Available cash |
| `invested_capital` | Decimal | Capital in positions |
| `total_value` | Decimal | Cash + invested |
| `realised_pnl` | Decimal | Total realised P&L |
| `unrealised_pnl` | Decimal | Total unrealised P&L |
| `peak_value` | Decimal | Highest portfolio value |
| `current_drawdown` | Decimal | Current drawdown % |
| `risk_lock_active` | bool | Whether RISK LOCK is engaged |
| `kill_switch_active` | bool | Whether KILL SWITCH is engaged |

### RiskSnapshot

| Attribute | Type | Description |
|-----------|------|-------------|
| `snapshot_id` | UUID | Unique identifier |
| `portfolio_id` | UUID | Portfolio |
| `timestamp` | datetime | Snapshot time (UTC) |
| `total_open_risk` | Decimal | Aggregate risk % |
| `daily_pnl` | Decimal | Day's P&L |
| `weekly_pnl` | Decimal | Week's P&L |
| `drawdown_pct` | Decimal | Current drawdown |
| `position_count` | int | Open positions |
| `sector_exposures` | dict | Per-sector allocation |
| `risk_level` | RiskLevel | NORMAL, ELEVATED, RISK_LOCK |

### AuditRecord

| Attribute | Type | Description |
|-----------|------|-------------|
| `audit_id` | UUID | Unique identifier |
| `timestamp` | datetime | Event time (UTC) |
| `event_type` | str | SIGNAL, PROPOSAL, APPROVAL, ORDER, etc. |
| `entity_type` | str | What entity was affected |
| `entity_id` | UUID | Affected entity |
| `actor` | str | SYSTEM, STRATEGY:{name}, USER, AI:{provider} |
| `action` | str | What happened |
| `details` | dict | Full context |
| `data_snapshot_ref` | str | None | Reference to data used |
| `strategy_version` | str | None | Strategy version |
| `risk_policy_version` | str | None | Risk policy version |
| `compliance_policy_version` | str | None | Compliance version |

## 3. Enumerations

```python
class Exchange(Enum):
    NSE = "NSE"
    BSE = "BSE"


class TradeSide(Enum):
    BUY = "BUY"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop-loss limit
    SL_M = "SL_M"  # Stop-loss market


class OrderStatus(Enum):
    CREATED = "CREATED"
    RISK_VALIDATED = "RISK_VALIDATED"
    COMPLIANCE_VALIDATED = "COMPLIANCE_VALIDATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class BrokerMode(Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class StrategyLifecycle(Enum):
    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    BACKTEST = "BACKTEST"
    VALIDATION = "VALIDATION"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"
    WALK_FORWARD = "WALK_FORWARD"
    ROBUSTNESS_TESTING = "ROBUSTNESS_TESTING"
    COST_TESTING = "COST_TESTING"
    PAPER_TRADING = "PAPER_TRADING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    LIMITED_LIVE = "LIMITED_LIVE"
    PRODUCTION = "PRODUCTION"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class MarketRegime(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    UNKNOWN = "UNKNOWN"


class RiskLevel(Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"  # 5% drawdown warning
    RISK_REDUCTION = "RISK_REDUCTION"  # 8% drawdown
    RISK_LOCK = "RISK_LOCK"  # 10% drawdown, hard lock


class ProposalStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"


class CorporateActionType(Enum):
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    DIVIDEND = "DIVIDEND"
    RIGHTS = "RIGHTS"
    MERGER = "MERGER"
    DEMERGER = "DEMERGER"
    SYMBOL_CHANGE = "SYMBOL_CHANGE"
    DELISTING = "DELISTING"
```

## 4. Key Relationships

```
Instrument 1──∞ OHLCV
Instrument 1──∞ CorporateAction
Instrument 1──∞ Signal
Strategy   1──∞ Signal
Signal     1──1 TradeProposal
TradeProposal 1──0..1 Order
Order      1──0..1 Position
Position   ∞──1 Portfolio
Portfolio  1──∞ RiskSnapshot
*          ∞──∞ AuditRecord
```

## 5. Aggregate Boundaries

| Aggregate Root | Contains |
|---------------|----------|
| `Instrument` | OHLCV bars, corporate actions |
| `Strategy` | Version history, parameters |
| `TradeProposal` | Signal reference, approval state |
| `Order` | Order lifecycle, fill data |
| `Position` | Entry/exit tracking, P&L |
| `Portfolio` | Positions, cash, risk state |
