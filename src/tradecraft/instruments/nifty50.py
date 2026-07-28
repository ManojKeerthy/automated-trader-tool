from datetime import date
from typing import Any

# Current list of Nifty 50 stock symbols on NSE
NIFTY50_SYMBOLS = [
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJAJFINSV",
    "BAJFINANCE",
    "BEL",
    "BHARTIARTL",
    "BPCL",
    "BRITANNIA",
    "CIPLA",
    "COALINDIA",
    "DRREDDY",
    "EICHERMOT",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "INDUSINDBK",
    "INFY",
    "ITC",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "LTM",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SUNPHARMA",
    "TATACONSUM",
    "TMPV",
    "TATASTEEL",
    "TCS",
    "TECHM",
    "TITAN",
    "TRENT",
    "ULTRACEMCO",
    "WIPRO",
]


def get_current_nifty50_constituents() -> list[dict[str, Any]]:
    """Return the list of current Nifty 50 constituents with default metadata."""
    constituents = []
    # Starting date for current constituents is default or when we start tracking
    start_tracking_date = date(2026, 1, 1)

    for symbol in NIFTY50_SYMBOLS:
        constituents.append(
            {
                "symbol": symbol,
                "exchange": "NSE",
                "isin": None,  # Will be updated by data provider
                "name": symbol.replace("BANK", " BANK").replace("MOTORS", " MOTORS").title(),
                "segment": "EQ",
                "is_active": True,
                "nifty50_member_from": start_tracking_date,
                "nifty50_member_to": None,
            }
        )
    return constituents
