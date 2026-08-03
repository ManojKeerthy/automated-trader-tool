# POINT-IN-TIME DATA ARCHITECTURE & UNIVERSE MANAGEMENT — START HERE

> **MANDATORY ARCHITECTURAL DIRECTIVE**:  
> Strategies and research feature processors MUST NEVER execute direct raw SQL queries against historical ticker symbols.
> All constituent lookups, market data queries, and corporate action adjustments MUST be routed through the `UniverseAPI` and `DataProvider` abstraction layers.

---

## 1. PURPOSE OF M3C.1 ARCHITECTURE

Milestone **M3C.1** establishes an institutional Point-in-Time Data Architecture that eliminates:
1. **Survivorship Bias**: Preventing current index constituents from being projected backwards into history.
2. **Lookahead Bias**: Gating queries to the simulation clock date $T$.
3. **Vendor Lock-in**: Decoupling ingestion from specific data providers (`DataProvider` interface).
4. **Symbol Identity Ambiguity**: Enforcing immutable `security_uuid` primary keys across symbol renames and ISIN reassignments.

---

## 2. DOCUMENTATION MAP

| Document | Description |
| :--- | :--- |
| [overview.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/overview.md) | High-level system architecture & component diagram. |
| [security_master.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/security_master.md) | Security Master design and `security_uuid` mapping. |
| [universe_registry.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/universe_registry.md) | Supported index universe definitions and dataset versioning. |
| [historical_membership.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/historical_membership.md) | Effective-dated point-in-time membership query engine. |
| [survivorship_bias.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/survivorship_bias.md) | Programmatic runtime survivorship guard rules. |
| [corporate_actions.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/corporate_actions.md) | Timestamped corporate action tracking. |
| [point_in_time_queries.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/point_in_time_queries.md) | Query flow through `UniverseAPI` and `DataProvider`. |
| [future_scaling.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/future_scaling.md) | Scaling path from NIFTY 50 to full NSE equity universe. |
| [implementation_notes.md](file:///c:/infiligence/automated-trader-tool/docs/research/universe/implementation_notes.md) | Developer & maintainer implementation details. |
