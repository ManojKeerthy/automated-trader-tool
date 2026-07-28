# ADR-005: Data, Timezone, and Calendar Handling

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution + resolved decisions)

## Context

Trading operates in the Indian market (NSE/BSE) with sessions in IST (Asia/Kolkata). The system must work correctly regardless of the host computer's local timezone and must handle trading calendars accurately.

## Decision

### Timestamps
- **Storage**: UTC for all persisted timestamps
- **Market logic**: Explicit `Asia/Kolkata` timezone via `zoneinfo.ZoneInfo("Asia/Kolkata")`
- **Display**: Convert to `Asia/Kolkata` for dashboard
- **Never**: Use the host computer's local timezone for any trading logic

### Trading Calendar
- **Authoritative source**: Official NSE/BSE published trading holidays and circulars
- **Implementation**: `exchange_calendars` Python library (or equivalent) validated against official data
- **Abstraction**: Internal `TradingCalendar` interface decouples consumers from library
- **Persistence**: Calendar used for backtests is persisted for reproducibility
- **Quality check**: Automated detection of disagreement between stored calendar and official exchange information

### Market Data Timezone
- Raw data from Zerodha is in IST
- Stored with explicit timezone annotation
- Converted as needed, never assumed

## Rationale

1. **Correctness**: Using local timezone would cause bugs when running from non-IST locations
2. **Reproducibility**: UTC storage ensures consistent timestamps across environments
3. **Calendar accuracy**: Library convenience with official verification prevents calendar errors
4. **Portability**: Works correctly in any timezone, critical for cloud deployment

## Consequences

- All `datetime` objects in the codebase must be timezone-aware
- Trading calendar must be validated before use in backtesting
- `exchange_calendars` library is a convenience, not truth — must be verified
- Calendar quality checks must run periodically
