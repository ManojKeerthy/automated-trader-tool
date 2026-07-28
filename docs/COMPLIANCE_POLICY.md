# TradeCraft — Compliance Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Compliance Philosophy

Compliance is a **first-class subsystem**, not an afterthought. Legal and regulatory compliance is the **#1 priority** in the system hierarchy.

**Fail-closed principle**: If legality or compliance is uncertain, DO NOT execute the affected action. Block it, log it, and flag for human review.

## 2. Relevant Authorities

| Authority | Jurisdiction | Relevance |
|-----------|-------------|-----------|
| **SEBI** (Securities and Exchange Board of India) | Securities market regulation | Primary regulator for equity trading |
| **NSE** (National Stock Exchange) | Exchange rules | Trading rules, margins, circuit breakers |
| **BSE** (Bombay Stock Exchange) | Exchange rules | Architectural support, not initially active |
| **Clearing corporations** (NSCCL/ICCL) | Settlement | Settlement obligations |
| **Depositories** (NSDL/CDSL) | Securities holding | Depository requirements |
| **Zerodha** | Broker requirements | Broker-specific rules and restrictions |

### RBI Applicability
RBI (Reserve Bank of India) governs monetary policy, banking, and foreign exchange. Do NOT assume RBI governs securities trading behaviour merely because the project operates in India. Determine jurisdiction from authoritative sources for each specific regulation.

## 3. Source Priority

When determining regulatory requirements:

| Priority | Source | Trust Level |
|----------|--------|-------------|
| 1 | Primary official regulator/exchange material (SEBI circulars, NSE notices) | HIGHEST |
| 2 | Official broker documentation (Zerodha support/docs) | HIGH |
| 3 | Other authoritative primary material | MODERATE |
| 4 | Reputable secondary interpretation | LOW |
| 5 | AI prior knowledge | LOWEST — never treat as current regulation |

Higher-priority sources override lower-priority sources in case of conflict.

## 4. Regulatory Knowledge Base

Maintain a versioned knowledge base storing:

| Field | Description |
|-------|-------------|
| `source` | Where the information came from |
| `authority` | Which regulatory body |
| `title` | Regulation/circular title |
| `circular_ref` | Reference/circular number |
| `publication_date` | When published |
| `effective_date` | When it takes effect |
| `retrieved_date` | When we obtained it |
| `url` | Link to source document |
| `applicability` | What it applies to |
| `extracted_obligations` | What we must do |
| `interpretation` | Our understanding |
| `confidence` | How confident we are |
| `affected_components` | Which system modules are impacted |

## 5. Regulatory Update Workflow

```
DISCOVER (new regulation/circular)
  ▼
RETRIEVE PRIMARY SOURCE
  ▼
ARCHIVE (store in knowledge base)
  ▼
EXTRACT (identify obligations)
  ▼
DIFF AGAINST CURRENT POLICY
  ▼
IMPACT ANALYSIS (which components affected?)
  ▼
FLAG UNCERTAINTY
  ▼
PROPOSE POLICY/CODE CHANGES
  ▼
TEST
  ▼
HUMAN APPROVAL (when required)
  ▼
DEPLOY
```

AI must NOT directly modify production code because regulation changed.

## 6. Initial Compliance Scope

For V1 paper trading with Nifty 50 cash equities:

### What We Must Verify
- Instrument is listed and actively traded on NSE
- No trading suspension on the instrument
- No regulatory restriction preventing trading
- Order type and parameters are valid for the exchange
- Trading during valid market hours
- Position limits (if applicable for retail)

### What We Track (for future live compliance)
- Trade reporting obligations
- Tax implications (STT, capital gains)
- Holding period classification (short-term vs long-term)

## 7. Compliance in Code

The compliance engine is **deterministic**. It validates every trade proposal against known rules before allowing execution.

```
Trade Proposal
  ▼
Compliance Check
  ├── PASS → Continue to human approval
  └── FAIL → Block trade, log reason, notify
```

If compliance status is UNKNOWN or UNCERTAIN → treat as FAIL (fail-closed).

## 8. Dashboard Visibility

The dashboard must show:
- Overall compliance status (GREEN / YELLOW / RED)
- Last regulatory knowledge base update
- Any flagged compliance uncertainties
- Compliance check results for each trade proposal
