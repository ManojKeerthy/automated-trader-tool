"""Index universe definitions for data ingestion.

SCOPE AND HONESTY NOTE
======================
These are **current** (as-of-ingestion) constituent lists. They are a bootstrap for
*data ingestion only* — deciding which symbols to fetch bars for.

They are NOT point-in-time membership and MUST NOT be used to define a backtest universe
directly. Doing so introduces survivorship bias: names that were in the index in 2016 but
were removed by 2026 are absent, so historical performance is measured only across
survivors. Point-in-time membership lives in `tradecraft.universe.historical_membership`
and must be populated from dated NSE index-change circulars before any result is reported.

To reduce (not eliminate) survivorship bias at ingestion time, the NIFTY 100 list below is
deliberately a *superset*: it includes names that have since been removed from the index
but were constituents during the 2015-2026 research window. Fetching a delisted or demoted
name costs one API call; omitting it silently biases every backtest.

Symbol notes:
- Zerodha trading symbols are used (e.g. LTIM, TMPV, LTM), which differ from some NSE
  historical tickers after mergers and renames.
- Renamed/merged predecessors are listed under HISTORICAL_SYMBOLS so their pre-merger
  history can still be fetched.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# ---------------------------------------------------------------------------------------
# NIFTY 50 — current constituents
# ---------------------------------------------------------------------------------------

NIFTY50_SYMBOLS: list[str] = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BEL", "BHARTIARTL",
    "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
    "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
    "LTM", "M&M", "MARUTI", "NESTLEIND", "NTPC",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SUNPHARMA", "TATACONSUM", "TATASTEEL", "TCS", "TECHM",
    "TITAN", "TMPV", "TRENT", "ULTRACEMCO", "WIPRO",
]

# ---------------------------------------------------------------------------------------
# NIFTY 100 — the additional ~50 names beyond the NIFTY 50
# ---------------------------------------------------------------------------------------

NIFTY_NEXT50_SYMBOLS: list[str] = [
    "ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM",
    "BAJAJHLDNG", "BANKBARODA", "BOSCHLTD", "CANBK", "CGPOWER",
    "CHOLAFIN", "DABUR", "DIVISLAB", "DLF", "DMART",
    "GAIL", "GODREJCP", "HAVELLS", "HAL", "HYUNDAI",
    "ICICIGI", "ICICIPRULI", "INDHOTEL", "INDIGO", "IOC",
    "IRFC", "JINDALSTEL", "JIOFIN", "JSWENERGY", "LICI",
    "LODHA", "LTIM", "MOTHERSON", "NAUKRI", "PFC",
    "PIDILITIND", "PNB", "RECLTD", "SHREECEM", "SHRIRAMFIN",
    "SIEMENS", "SWIGGY", "TATAPOWER", "TORNTPHARM", "TVSMOTOR",
    "UNITDSPR", "VBL", "VEDL", "ZOMATO", "ZYDUSLIFE",
]

# ---------------------------------------------------------------------------------------
# Names that were NIFTY 100 constituents during 2015-2026 but have since been removed,
# renamed, merged or delisted. Included to reduce survivorship bias at ingestion time.
# Some will fail to resolve against the live Kite instrument dump — that is expected and
# is reported, not fatal.
# ---------------------------------------------------------------------------------------

HISTORICAL_SYMBOLS: list[str] = [
    "HDFC",          # merged into HDFCBANK, Jul 2023
    "LTI",           # merged with MINDTREE -> LTIM, Nov 2022
    "MINDTREE",      # merged into LTIM
    "LTIM",          # kept: renamed to LTM in some feeds
    "TATAMOTORS",    # demerged -> TMPV / TATAMOTORS
    "SHRIRAMCIT",    # merged -> SHRIRAMFIN
    "SRTRANSFIN",    # renamed -> SHRIRAMFIN
    "MCDOWELL-N",    # renamed -> UNITDSPR
    "CADILAHC",      # renamed -> ZYDUSLIFE
    "UBL", "COLPAL", "MARICO", "BERGEPAINT", "PEL",
    "AUROPHARMA", "LUPIN", "BIOCON", "GLENMARK", "TORNTPOWER",
    "IDEA", "YESBANK", "RBLBANK", "BANDHANBNK", "FEDERALBNK",
    "IDFCFIRSTB", "PETRONET", "NMDC", "SAIL", "NATIONALUM",
    "CONCOR", "BHEL", "BHARATFORG", "ASHOKLEY", "ESCORTS",
    "PAGEIND", "MUTHOOTFIN", "MFSL", "SUNTV", "ZEEL",
    "PVRINOX", "ACC", "RAMCOCEM", "EXIDEIND", "APOLLOTYRE",
    "GMRAIRPORT", "IGL", "OFSS", "MPHASIS", "PERSISTENT",
    "COFORGE", "POLYCAB", "SRF", "UPL", "PIIND",
]


# ---------------------------------------------------------------------------------------
# SYMBOL SUCCESSION MAP
# ---------------------------------------------------------------------------------------
# Maps a historical trading symbol to the symbol that carries its price history forward,
# with the effective date of the change.
#
# These names do NOT resolve against a current broker instrument dump, because the listing
# no longer exists. Re-adding them as fresh symbols would create empty instruments; the
# correct handling is to record the succession so that point-in-time universe membership
# and pre-event history attach to the right security.
#
# `successor = None` means the history terminates and does not continue anywhere (genuine
# delisting or a demerger where no single successor carries the full history).
#
# IMPORTANT: this table is a research aid, not verified reference data. Each entry needs
# confirming against the NSE circular for that event before any result depending on it is
# reported. Effective dates in particular are approximate where noted.
SYMBOL_SUCCESSION: dict[str, dict[str, Any]] = {
    "HDFC": {"successor": "HDFCBANK", "effective": date(2023, 7, 13), "event": "MERGER",
             "note": "HDFC Ltd merged into HDFC Bank."},
    "LTI": {"successor": "LTIM", "effective": date(2022, 11, 14), "event": "MERGER",
            "note": "L&T Infotech merged with Mindtree to form LTIMindtree."},
    "MINDTREE": {"successor": "LTIM", "effective": date(2022, 11, 14), "event": "MERGER",
                 "note": "Mindtree merged into LTIMindtree."},
    "LTIM": {"successor": "LTM", "effective": None, "event": "RENAME",
             "note": "Ticker differs by feed; confirm which form Kite serves."},
    "SRTRANSFIN": {"successor": "SHRIRAMFIN", "effective": date(2022, 11, 25), "event": "RENAME",
                   "note": "Shriram Transport Finance renamed after amalgamation."},
    "SHRIRAMCIT": {"successor": "SHRIRAMFIN", "effective": date(2022, 11, 25), "event": "MERGER",
                   "note": "Shriram City Union Finance merged into Shriram Finance."},
    "MCDOWELL-N": {"successor": "UNITDSPR", "effective": None, "event": "RENAME",
                   "note": "United Spirits ticker change; confirm effective date."},
    "CADILAHC": {"successor": "ZYDUSLIFE", "effective": date(2022, 2, 21), "event": "RENAME",
                 "note": "Cadila Healthcare renamed Zydus Lifesciences."},
    "TATAMOTORS": {"successor": None, "effective": date(2025, 10, 14), "event": "DEMERGER",
                   "note": "Demerged into commercial and passenger vehicle entities. No single "
                           "successor carries the full history - splicing it onto either side "
                           "creates a fictitious continuous series."},
    "ZOMATO": {"successor": "ETERNAL", "effective": None, "event": "RENAME",
               "note": "Corporate rename; confirm the ticker Kite serves and the date."},
    "PEL": {"successor": None, "effective": None, "event": "DEMERGER",
            "note": "Piramal Enterprises demerged Piramal Pharma. Verify treatment."},
}


def resolve_successor(symbol: str) -> str | None:
    """Return the symbol carrying `symbol`'s history forward, or None if it terminates."""
    entry = SYMBOL_SUCCESSION.get(symbol.strip().upper())
    return entry["successor"] if entry else None


def unresolved_symbol_guidance(symbols: list[str]) -> list[str]:
    """Explain each unresolved symbol rather than silently dropping it.

    A symbol that fails to resolve is not noise. It is either a survivorship-bias hazard
    (the name existed during the research window and its absence biases results) or a
    succession that needs mapping. Both need a decision; neither should be ignored.
    """
    lines: list[str] = []
    for s in symbols:
        entry = SYMBOL_SUCCESSION.get(s.upper())
        if entry is None:
            lines.append(f"{s}: UNKNOWN - not in the succession map. Verify against NSE.")
        elif entry["successor"] is None:
            lines.append(
                f"{s}: {entry['event']} with no single successor. {entry['note']}"
            )
        else:
            eff = entry["effective"].isoformat() if entry["effective"] else "date UNCONFIRMED"
            lines.append(
                f"{s}: {entry['event']} -> {entry['successor']} ({eff}). {entry['note']}"
            )
    return lines


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


NIFTY100_SYMBOLS: list[str] = _dedupe(NIFTY50_SYMBOLS + NIFTY_NEXT50_SYMBOLS)

# Superset used for ingestion: current NIFTY 100 plus historical constituents.
NIFTY100_INGESTION_SYMBOLS: list[str] = _dedupe(NIFTY100_SYMBOLS + HISTORICAL_SYMBOLS)


UNIVERSES: dict[str, list[str]] = {
    "NIFTY50": NIFTY50_SYMBOLS,
    "NIFTY100": NIFTY100_SYMBOLS,
    "NIFTY100_FULL": NIFTY100_INGESTION_SYMBOLS,
}


def resolve_universe(name: str, include_historical: bool = True) -> list[str]:
    """Return the symbol list for a named universe.

    Args:
        name: One of NIFTY50, NIFTY100, NIFTY100_FULL (case-insensitive).
        include_historical: When True and name is NIFTY100, returns the survivorship-reduced
            superset including removed/renamed constituents. Strongly recommended for
            ingestion.

    Raises:
        ValueError: If the universe name is unknown.
    """
    key = name.strip().upper()
    if key == "NIFTY100" and include_historical:
        key = "NIFTY100_FULL"
    if key not in UNIVERSES:
        raise ValueError(f"Unknown universe '{name}'. Available: {sorted(UNIVERSES)}")
    return list(UNIVERSES[key])


def build_constituent_records(
    symbols: list[str], tracking_start: date | None = None
) -> list[dict[str, Any]]:
    """Build instrument seed records for the given symbols.

    ISIN, name, tick size, lot size and instrument_token are intentionally left unset —
    they are authoritative only from the broker instrument dump and are populated by the
    instrument sync step. Inventing them here is how placeholder data gets into a research
    database.
    """
    start = tracking_start or date.today()
    return [
        {
            "symbol": symbol,
            "exchange": "NSE",
            "segment": "EQ",
            "isin": None,
            "name": None,
            "is_active": True,
            "tracking_from": start,
        }
        for symbol in symbols
    ]
