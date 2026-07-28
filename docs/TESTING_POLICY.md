# TradeCraft — Testing Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Testing Philosophy

Automated tests are mandatory. Financial/risk invariants deserve especially strong testing. A bug in risk management can cause real financial loss.

## 2. Test Categories

### Unit Tests (`tests/unit/`)
- Test individual functions and classes in isolation
- Fast execution, no external dependencies
- Mock external services and database

### Integration Tests (`tests/integration/`)
- Test module interactions
- May require database (Docker PostgreSQL)
- Test data pipeline end-to-end
- Test API endpoints

### Property / Invariant Tests (`tests/property/`)
- Test system invariants that must ALWAYS hold
- Use property-based testing (e.g., Hypothesis library)

### Regression Tests
- Prevent previously fixed bugs from recurring
- Added whenever a bug is fixed

### Data Quality Tests
- Validate market data integrity
- Check for missing/duplicate/impossible values
- Verify corporate action adjustments

### Backtest Correctness Tests
- Verify backtest engine produces known results for known inputs
- Test bias defense mechanisms

### Risk Rule Tests
- Every risk limit must have corresponding tests
- Test boundary conditions (at limit, over limit)

### Compliance Rule Tests
- Every compliance rule must have corresponding tests
- Test fail-closed behaviour

### Broker Adapter Contract Tests
- Paper and live adapters must satisfy the same contract
- Test error handling paths

### Failure / Recovery Tests
- Test behaviour when external services fail
- Test RISK LOCK and KILL SWITCH activation
- Test graceful degradation

## 3. Critical Invariants (Must ALWAYS Pass)

```python
# A rejected trade cannot reach execution
def test_rejected_trade_cannot_execute(): ...

# A trade exceeding risk limits cannot reach execution
def test_risk_limit_breach_blocks_execution(): ...

# Paper mode cannot submit a live order
def test_paper_mode_cannot_submit_live_order(): ...

# RISK LOCK prevents new exposure
def test_risk_lock_blocks_new_positions(): ...

# Stale data prevents affected trading decisions
def test_stale_data_blocks_trading(): ...

# An LLM cannot bypass deterministic risk/compliance controls
def test_ai_cannot_bypass_risk_controls(): ...

# Absent mode configuration defaults to PAPER
def test_default_mode_is_paper(): ...

# Kill switch cancels all pending orders
def test_kill_switch_cancels_orders(): ...
```

## 4. Cross-Platform Testing

### Requirement
The same market data + strategy version + configuration + portfolio state must produce **equivalent trading decisions** across all supported operating systems.

### CI Matrix
| OS | Priority | Purpose |
|----|----------|---------|
| Linux | Required | Production environment |
| Windows | Required | Primary dev environment |
| macOS | Best effort | Secondary dev environment |

### Determinism
- Platform-specific differences must NEVER silently change: signals, position sizing, risk decisions, compliance decisions, order intent, portfolio calculations
- Document explicitly any numerical tolerances (floating-point)
- Use `decimal.Decimal` for financial calculations where precision matters

## 5. Test Infrastructure

- **Framework**: pytest
- **Coverage**: pytest-cov (target: high coverage for risk/compliance)
- **Property testing**: Hypothesis (for invariant tests)
- **Fixtures**: `tests/fixtures/` for test data
- **CI**: GitHub Actions (see DEPLOYMENT.md)

## 6. Test Data

- Use fixture-based test data, not live API calls in tests
- Test fixtures represent known-correct scenarios
- Include edge cases: corporate actions, circuit breakers, zero volume, market holidays
