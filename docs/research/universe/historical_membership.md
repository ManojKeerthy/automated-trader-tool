# HISTORICAL MEMBERSHIP ENGINE SPECIFICATION

The `HistoricalMembershipEngine` maintains effective-dated index inclusion and exclusion intervals (`effective_from` $\rightarrow$ `effective_to`).

## Point-in-Time Query Logic:
`get_constituents(query_date, universe_id)` evaluates:
$$\text{Constituents}(T) = \{ s \in S \mid \text{effective\_from}(s) \le T \land ( \text{effective\_to}(s) = \text{None} \lor T \le \text{effective\_to}(s) ) \}$$

This guarantees zero survivorship bias during historical backtests.
