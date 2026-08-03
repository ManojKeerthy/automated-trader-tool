# PLAYBOOK: EXPERIMENT EXECUTION

1. Verify dataset firewall status (`DEVELOPMENT` only).
2. Fetch registered features via `ResearchClient`.
3. Execute single backtest run under `EndOfBacktestPolicy.FORCE_CLOSE`.
4. Register experiment run record with environment metadata.
5. Generate automated Markdown & JSON reports.
