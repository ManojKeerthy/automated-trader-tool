# TradeCraft — Risk Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28
>
> These are INITIAL PAPER-TRADING PARAMETERS for ₹50,000 portfolio.
> Not claims of mathematically optimal values.

## 1. Risk Philosophy

Risk management is the system's most important operational function after compliance. It is implemented as **deterministic software**. LLMs have **zero authority** to bypass, modify, or override risk controls.

Changes to risk parameters require:
- Empirical justification
- Versioning
- Testing
- Appropriate human approval

Risk limits must NEVER be optimised merely to maximise historical returns.

## 2. Per-Trade Risk

| Parameter | Value | At ₹50,000 |
|-----------|-------|-------------|
| Target risk per trade | 0.5% of portfolio equity | ≈ ₹250 |
| Hard maximum risk per trade | 0.75% of portfolio equity | ≈ ₹375 |

Risk per trade = `quantity × (entry_price - stop_loss_price)`.

If a trade cannot be sized to fit within risk limits with at least 1 share, the trade is rejected.

## 3. Portfolio Risk Limits

| Parameter | Value |
|-----------|-------|
| Maximum total open portfolio risk | 2.0% of equity |
| Maximum single-stock capital allocation | 20% of equity |
| Maximum sector capital exposure | 40% of equity |
| Maximum simultaneous positions | 5 |

Position count is subordinate to portfolio risk and available capital. Having 5 positions is not a target — it is a ceiling.

## 4. Loss Guards

| Guard | Threshold | Action |
|-------|-----------|--------|
| Daily loss | 1.5% of portfolio equity | Block new entries for the day |
| Weekly loss | 3.0% of portfolio equity | Block new entries for the week |

Loss guards reset at the start of the next period.

## 5. Drawdown Controls

| Drawdown Level | State | Actions |
|----------------|-------|---------|
| < 5% | NORMAL | Normal operation |
| ≥ 5% | ELEVATED / WARNING | Reduce willingness to add risk; tighten screening criteria; log warning |
| ≥ 8% | RISK_REDUCTION | Actively reduce exposure; tighten stops where strategy allows; no new positions unless exceptionally high conviction; require human awareness |
| ≥ 10% | RISK_LOCK (HARD) | **No new positions.** Prioritise capital preservation. Manage existing positions for risk reduction. Require human review before any new exposure. |

Drawdown is measured from portfolio peak value.

## 6. RISK LOCK

When RISK LOCK activates:

1. **Block all new position entries** — no exceptions
2. **Prioritise capital preservation** — existing positions managed for risk reduction
3. **Protective stops remain active** — never removed during RISK LOCK
4. **Log the event** with full portfolio state
5. **Notify user** via dashboard
6. **Require human review** before RISK LOCK can be cleared

RISK LOCK cannot be cleared by:
- AI
- Automatic timer
- Strategy signal
- Portfolio recovery alone (recovery is necessary but insufficient — human review required)

## 7. KILL SWITCH

The KILL SWITCH is a global emergency control that:

1. **Immediately blocks all new orders**
2. **Cancels all pending/open orders**
3. **Optionally closes all positions** (if configured and market is open)
4. **Logs the event** with full system state
5. **Requires explicit human intervention** to reset

KILL SWITCH triggers:
- Manual user activation
- System health critical failure
- Data integrity failure affecting trading decisions
- Broker communication complete failure during market hours (with open positions)
- Any condition where the system cannot confidently manage risk

## 8. Position Sizing

Position sizing is **systematic and volatility-aware**.

Base approach:
```
risk_amount = portfolio_equity × risk_per_trade_pct
stop_distance = entry_price - stop_loss_price
raw_quantity = risk_amount / stop_distance
quantity = floor(raw_quantity)  # Round down, never up
```

Additional constraints applied:
- Maximum single-stock allocation check
- Maximum sector exposure check
- Available cash check
- Minimum quantity (must be ≥ 1)
- Maximum portfolio risk check (adding this position)

If any constraint fails, the trade is rejected or resized downward.

## 9. Prohibited Behaviours

The following are **explicitly prohibited** in code and policy:

| Behaviour | Why Prohibited |
|-----------|---------------|
| **Martingale** (doubling down after losses) | Catastrophic loss risk |
| **Revenge trading** (trading to recover losses) | Emotional, not systematic |
| **Uncapped leverage** | Catastrophic loss risk |
| **Doubling risk following losses** | Compounds drawdown |
| **Averaging down solely because price declined** | Not a valid strategy rationale |
| **Removing/widening stops to avoid realising losses** | Destroys risk management |
| **Overriding risk limits for "high conviction"** | Conviction is not a risk parameter |

## 10. Protective vs Discretionary Exits

### Protective Exits (must not depend on human availability)
- Stop-loss orders
- Emergency risk reduction (RISK LOCK actions)
- KILL SWITCH actions
- Time-based invalidation of pending entries

### Discretionary Exits (should request human approval)
- Profit target reached
- Strategy-generated exit signals
- Manual position closing
- Partial profit-taking

## 11. Special Situations

### Weekend Holding
- Strategies may hold over weekends when justified by validated rules
- Weekend gap risk should be considered in position sizing

### Earnings / Corporate Events
- Holding through earnings must be an explicit strategy decision, not a default
- Event risk should be factored into risk calculations

### Stale Data
- If market data is stale beyond acceptable thresholds, affected trading decisions must be suspended
- Protective stops on existing positions must remain active

### Abnormal Market Conditions
- Circuit breaker events, extreme volatility, or market disruptions should trigger heightened risk awareness
- System should not attempt to trade during market disruptions

## 12. Version History

| Version | Date | Changes | Approved By |
|---------|------|---------|-------------|
| 1.0.0 | 2026-07-28 | Initial paper-trading parameters | User (constitution) |
