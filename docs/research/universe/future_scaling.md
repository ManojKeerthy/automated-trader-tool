# FUTURE SCALING ARCHITECTURE SPECIFICATION

The Point-in-Time Data Architecture supports scaling across universe sizes via configuration:
- `NIFTY 50` $\rightarrow$ `NIFTY 100` $\rightarrow$ `NIFTY 200` $\rightarrow$ `NIFTY 250` $\rightarrow$ `NIFTY 500` $\rightarrow$ `Entire NSE Equity Universe` $\rightarrow$ `Full Indian Equity Market`.

No code modifications are required to add new universes; only registering a new `UniverseDefinition` and seeding membership records.
