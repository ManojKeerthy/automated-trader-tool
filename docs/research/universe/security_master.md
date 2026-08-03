# SECURITY MASTER ARCHITECTURE SPECIFICATION

The `SecurityMaster` acts as the authoritative catalog mapping symbols and ISINs to an immutable internal `security_uuid` (UUID4 string).

## Key Design Principles:
1. **Ticker Symbols are Attributes**: Ticker symbols change over time (e.g. `M&M` $\rightarrow$ `MAHMRA`, `TATAMOTORS`). Symbols are stored in effective-dated `SymbolHistoryRecord` entries.
2. **ISIN Mapping**: ISIN code mappings are maintained alongside exchange ticker symbols.
3. **IPO & Delisting Boundaries**: Each security stores explicit `listing_date` and `delisting_date` attributes.
