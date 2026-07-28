# TradeCraft — Regulatory Sources

> Version: 1.0.0 | Status: INITIAL | Last Updated: 2026-07-28
>
> This document tracks authoritative regulatory sources. It must be kept current.

## 1. Source Priority

See [COMPLIANCE_POLICY.md](COMPLIANCE_POLICY.md) § 3 for the full priority hierarchy.

## 2. Primary Authorities

### SEBI (Securities and Exchange Board of India)
- **Website**: https://www.sebi.gov.in
- **Circulars**: https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=2
- **Relevance**: Primary regulator for securities markets, investor protection, market integrity
- **Key areas**: Trading rules, disclosure requirements, algorithmic/automated trading regulations, insider trading, market manipulation

### NSE (National Stock Exchange of India)
- **Website**: https://www.nseindia.com
- **Circulars**: https://www.nseindia.com/regulations/exchange-circulars
- **Trading holidays**: https://www.nseindia.com/resources/exchange-communication-holidays
- **Corporate actions**: https://www.nseindia.com/companies-listing/corporate-filings-actions
- **Relevance**: Exchange rules, trading hours, circuit breakers, listing requirements

### BSE (Bombay Stock Exchange)
- **Website**: https://www.bseindia.com
- **Relevance**: Architecturally supported but not initially active

### Zerodha (Broker)
- **Kite Connect docs**: https://kite.trade/docs/connect/v3/
- **Support/Z-Connect**: https://zerodha.com/z-connect/
- **Charges**: https://zerodha.com/charges
- **Relevance**: Broker-specific rules, API capabilities, fee structure

## 3. Known Regulatory Areas

### SEBI Requirements (to be researched per milestone)
| Area | Status | Notes |
|------|--------|-------|
| Algorithmic trading rules for retail | UNRESOLVED | Need to determine if personal systematic trading qualifies as "algo trading" under SEBI definitions |
| Short selling regulations | NOT_APPLICABLE | V1 does not short |
| Insider trading prevention | ACKNOWLEDGED | Platform must not facilitate insider trading |
| Market manipulation | ACKNOWLEDGED | Strategy validation must ensure compliance |
| Order-to-trade ratio limits | UNRESOLVED | May apply to automated systems |

### NSE Trading Rules
| Area | Status | Notes |
|------|--------|-------|
| Market hours | KNOWN | Pre-open: 9:00-9:08, Normal: 9:15-15:30 IST |
| Circuit breakers | KNOWN | Index-wide and stock-specific limits exist |
| Trading holidays | KNOWN | Published annually, verified against `exchange_calendars` |
| Special sessions | KNOWN | Muhurat trading, special Saturday sessions |

### Transaction Costs (to be verified before live trading)
| Component | Approximate Rate | Source | Verified |
|-----------|-----------------|--------|----------|
| Brokerage (delivery) | ₹0 | Zerodha | UNVERIFIED |
| STT | 0.1% buy+sell | SEBI/NSE | UNVERIFIED |
| Exchange charges | ~0.00297% | NSE | UNVERIFIED |
| GST | 18% on charges | Government | UNVERIFIED |
| SEBI fee | 0.0001% | SEBI | UNVERIFIED |
| Stamp duty | ~0.015% on buy | State | UNVERIFIED |

## 4. Unresolved Regulatory Questions

1. **SEBI algo trading classification**: Does personal systematic trading via Kite Connect API constitute "algorithmic trading" under SEBI's current framework? If so, what additional requirements apply?
2. **Tax reporting**: What are the tax reporting obligations for systematic trading?
3. **Position reporting**: Are there position reporting requirements for retail systematic traders?

These must be researched before M6 (Compliance System) and definitely before M11 (Live Integration).
