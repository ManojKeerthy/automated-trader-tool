"""REMOVED 2026-08-06 — THIS SCRIPT NEVER FETCHED REAL DATA.

Despite its name, this script FABRICATED prices and stamped them
`source = "ZERODHA_KITE_EOD"`. It is the direct cause of Research Cycles 1 and 2 being
conducted entirely against synthetic data.

See: docs/research/REPO_AUDIT_2026-08-06.md

Replacements:
  Real NSE data      ->  python -m tradecraft data backfill --universe NIFTY100
                             --start 2015-01-01
  Synthetic fixture  ->  python scratch/generate_synthetic_fixture.py
                             --i-understand-this-is-fake --db-path data/synthetic_fixture.db

This stub is retained (rather than deleted) so that any script, notebook, or agent still
referencing the old path fails loudly instead of silently regenerating fake data.
"""

raise SystemExit(
    "seed_real_market_bars.py has been removed - it never fetched real data.\n"
    "It fabricated prices and labelled them ZERODHA_KITE_EOD, invalidating two research "
    "cycles.\n\n"
    "  Real data:         python -m tradecraft data backfill --universe NIFTY100 "
    "--start 2015-01-01\n"
    "  Synthetic fixture: python scratch/generate_synthetic_fixture.py "
    "--i-understand-this-is-fake --db-path data/synthetic_fixture.db\n\n"
    "See docs/research/REPO_AUDIT_2026-08-06.md"
)
