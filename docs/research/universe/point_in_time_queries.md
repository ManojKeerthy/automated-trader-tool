# POINT-IN-TIME QUERY FLOW SPECIFICATION

Strategies and feature stores query historical universes exclusively through `UniverseAPI`:

```python
# Strategy Query Example
constituents = universe_api.get_constituents("NIFTY250", query_date=date(2019, 6, 15))
for sec in constituents:
    bars = data_portal.get_history(sec.security_uuid, start_date, end_date)
```
Direct SQL execution or raw symbol string lookups are strictly prohibited.
