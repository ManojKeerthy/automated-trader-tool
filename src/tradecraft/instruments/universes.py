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
- Zerodha trading symbols are used (e.g. LTM, TMPV), which differ from some NSE historical
  or commonly-reported tickers after mergers and renames. VERIFIED 2026-08-06 directly
  against Kite's live instrument dump: LTIMindtree's Kite tradingsymbol is "LTM", not
  "LTIM" - most financial media and aggregator sites report "LTIM" (that IS the widely-used
  public ticker), but Kite's own `kite.instruments('NSE')` dump has no "LTIM" entry at all,
  only "LTM" (instrument_token 4561409). Do not trust external sources over a direct query
  against the actual provider for this kind of fact - see PROJECT_STATUS.md.
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
    "LTI",           # merged with MINDTREE -> LTM, Nov 2022
    "MINDTREE",      # merged into LTM
    # "LTIM" removed 2026-08-06: not a real, distinct Kite ticker (see the Symbol notes
    # above). It was a redundant, always-unresolved entry; LTI + MINDTREE already cover the
    # pre-merger history and LTM (in NIFTY50_SYMBOLS) covers the current, live entity.
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
    # Verified 2026-08-06 against real sources; "effective" is the record date wherever a
    # source gave one (NSE/exchange convention: the date determining which shareholders
    # receive the new security is the operationally relevant date for a price-series
    # splice), falling back to the announced effective date when no record date was found.
    "HDFC": {"successor": "HDFCBANK", "effective": date(2023, 7, 13), "event": "MERGER",
             "note": "HDFC Ltd merged into HDFC Bank. Legal merger effective date 2023-07-01; "
                     "2023-07-13 is the record date used here (HDFC Bank press release, "
                     "Business Standard 'HDFC twins gain up to 3% after they fix July 13 as "
                     "record date for merger'). Ratio: 42 HDFCBANK shares for every 25 HDFC "
                     "Ltd shares."},
    "LTI": {"successor": "LTM", "effective": date(2022, 11, 14), "event": "MERGER",
            "note": "L&T Infotech merged with Mindtree to form LTIMindtree, publicly known as "
                    "'LTIM' but Kite's actual tradingsymbol is 'LTM' (verified 2026-08-06 "
                    "against the live instrument dump - see Symbol notes above). 2022-11-14 "
                    "is the date the merged entity began operating (BusinessWire/Business "
                    "Standard, 'LTI and Mindtree to Start Operating as a Merged Entity From "
                    "November 14, 2022'); the record date for share allotment to Mindtree "
                    "shareholders was separately fixed as 2022-11-24, ratio 73 LTI shares per "
                    "100 Mindtree shares - both dates sourced, kept 11-14 here for the "
                    "operational split."},
    "MINDTREE": {"successor": "LTM", "effective": date(2022, 11, 14), "event": "MERGER",
                 "note": "Mindtree merged into the entity publicly known as LTIMindtree, "
                         "Kite tradingsymbol 'LTM'. Same sourcing as LTI above; record date "
                         "for share allotment was 2022-11-24."},
    "SRTRANSFIN": {"successor": "SHRIRAMFIN", "effective": date(2022, 11, 30), "event": "RENAME",
                   "note": "Shriram Transport Finance renamed Shriram Finance after "
                           "amalgamation. CORRECTED 2026-08-06: was 2022-11-25, wrong; the "
                           "actual record date is 2022-11-30 (search explicitly disambiguated "
                           "this from the prior incorrect date; STFC fixed Nov 30, 2022 as "
                           "record date for the Shriram Capital / Shriram City Union merger)."},
    "SHRIRAMCIT": {"successor": "SHRIRAMFIN", "effective": date(2022, 11, 30), "event": "MERGER",
                   "note": "Shriram City Union Finance merged into Shriram Finance. CORRECTED "
                           "2026-08-06: was 2022-11-25, wrong; same 2022-11-30 record date as "
                           "SRTRANSFIN above - one consolidated scheme covering both entities."},
    "MCDOWELL-N": {"successor": "UNITDSPR", "effective": date(2024, 6, 7), "event": "RENAME",
                   "note": "United Spirits ticker changed from MCDOWELL-N to UNITDSPR. "
                           "RESOLVED 2026-08-06: effective 2024-06-07, sourced from Zerodha's "
                           "own bulletin, 'Change in stock name and symbol for United Spirits "
                           "Limited'."},
    "CADILAHC": {"successor": "ZYDUSLIFE", "effective": date(2022, 2, 24), "event": "RENAME",
                 "note": "Cadila Healthcare renamed Zydus Lifesciences. CORRECTED 2026-08-06: "
                         "was 2022-02-21, wrong; the actual date is 2022-02-24, confirmed by "
                         "the NSE press-release filing itself "
                         "(nsearchives.nseindia.com/corporate/CADILAHC_24022022143246_"
                         "PressRelease24022022.pdf - the filename encodes 24-02-2022)."},
    "TATAMOTORS": {"successor": None, "effective": date(2025, 10, 14), "event": "DEMERGER",
                   "note": "Demerged into commercial vehicles (TML Commercial Vehicles Ltd) "
                           "and passenger vehicles (renamed Tata Motors Passenger Vehicles "
                           "Ltd, retains the TATAMOTORS listing). No single successor carries "
                           "the full history - splicing it onto either side creates a "
                           "fictitious continuous series. VERIFIED 2026-08-06: 2025-10-14 "
                           "record date confirmed independently (Business Standard, 'Tata "
                           "Motors fixes October 14 as record date for demerger, stock rallies "
                           "5%'; scheme effective 2025-10-01, 1:1 share entitlement)."},
    "ZOMATO": {"successor": "ETERNAL", "effective": date(2025, 4, 9), "event": "RENAME",
               "note": "Corporate rename to Eternal Limited; ticker changed ZOMATO -> "
                       "ETERNAL. RESOLVED 2026-08-06: effective 2025-04-09, confirmed by "
                       "multiple sources (Angel One, Bajaj Broking, India Infoline all agree "
                       "on this date for the exchange symbol change; the underlying corporate "
                       "name change was registered 2025-03-20)."},
    "PEL": {"successor": None, "effective": date(2022, 8, 30), "event": "DEMERGER",
            "note": "Piramal Enterprises demerged Piramal Pharma. RESOLVED 2026-08-06: ex-date "
                    "2022-08-30, record date 2022-09-01 (Business Standard, 'Piramal "
                    "Enterprises shares trade ex-demerger; stock surges 9% intra-day'). Ratio: "
                    "4 Piramal Pharma shares (Rs 10 each) per 1 Piramal Enterprises share "
                    "(Rs 2 each). successor=None is deliberate and correct, not unresolved: "
                    "Piramal Pharma is a separately listed entity (listed 2022-10-19), not a "
                    "single successor carrying PEL's full history forward."},
}

# CORRECTED 2026-08-06 (see also the Symbol notes at the top of this file): an earlier pass
# this session removed "LTIM" from this map on the theory that "LTIM" was the correct live
# Kite ticker and the map entry was backwards. That was wrong, based on trusting general web
# search results over a direct check. Verified properly by querying Kite's own
# `kite.instruments('NSE')` dump directly: it contains "LTM" (instrument_token 4561409) and
# no "LTIM" entry at all. "LTIM" is the ticker most financial media and aggregator sites
# report, but it is not what Kite itself serves. There is therefore no live "LTIM" symbol to
# protect here, and no succession entry is needed for it either - LTI and MINDTREE above
# already point their successor at "LTM" directly, and "LTIM" was removed from
# HISTORICAL_SYMBOLS as a redundant, always-unresolvable entry. Lesson: for empirically
# checkable facts about what this project's own data provider serves, query it directly
# rather than trusting external sources - the same principle CLAUDE.md already establishes
# for market data more broadly.
assert "LTIM" not in SYMBOL_SUCCESSION, "LTIM was never a real Kite ticker - do not re-add"


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
