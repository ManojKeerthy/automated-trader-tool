# CORPORATE ACTION REGISTRY SPECIFICATION

The `CorporateActionRegistry` stores timestamped corporate action records (`CorporateActionRecord`):
- `SPLIT`: Stock splits adjusting historical prices and quantities.
- `BONUS`: Bonus share issuances.
- `MERGER` / `DEMERGER`: Corporate restructurings.
- `SYMBOL_CHANGE` / `NAME_CHANGE`: Ticker or company name reassignments.
- `DELISTING` / `RELISTING`: Security listing status changes.
