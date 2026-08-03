# SURVIVORSHIP BIAS PROTECTION GUARD SPECIFICATION

The `SurvivorshipGuard` enforces programmatic runtime protection against lookahead and survivorship errors:

1. **IPO Listing Boundary Check**: Raises `SurvivorshipBiasError` if a query accesses a security on date $T < \text{listing\_date}$.
2. **Delisting Boundary Check**: Raises `SurvivorshipBiasError` if a query accesses a security on date $T > \text{delisting\_date}$.
3. **Symbol Rename Boundary Check**: Validates symbol queries against effective historical rename intervals.
4. **Backward Constituent Projection Check**: Blocks strategies from using current constituent lists for historical queries without verified membership records.
