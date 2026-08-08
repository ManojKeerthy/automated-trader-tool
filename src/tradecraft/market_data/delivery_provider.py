"""NSE Security-Wise Delivery Position ingestion.

Source: NSE's own daily "MTO" (Market Type wise Order details / delivery position) report,
published free with no login at a stable archive URL. Verified live 2026-08-08:

    https://nsearchives.nseindia.com/archives/equities/mto/MTO_{DDMMYYYY}.DAT

covers 2014-08-11 through the present (matching this project's existing MarketBar coverage),
requires only a browser-like User-Agent header (no session/cookie dance, no API key). Not
available from Kite Connect - checked directly against its own API documentation, which
provides no fundamentals or delivery data of any kind.

File format (empirically inspected, not assumed):
    Line 1: title
    Line 2: "10,MTO,<ddmmyyyy>,...,..." (header/record-count line)
    Line 3: "Trade Date <DD-MON-YYYY>,..."
    Line 4: column header labels (informational only - the label count does not match the
        actual data column count, so parsing here is by fixed field POSITION, not by label)
    Line 5+: data rows, "20,<sr_no>,<symbol>,<series>,<traded_qty>,<delivery_qty>,<delivery_pct>"

Only "20,"-prefixed rows are data; only "EQ" series rows are kept (matches this project's
equity-only universe - BE/BZ/GS/other series are different trading categories, not part of
the tradeable universe).

A non-trading day returns HTTP 404 - this is expected and not an error.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import requests

logger = logging.getLogger("tradecraft.delivery_provider")

MTO_URL_TEMPLATE = "https://nsearchives.nseindia.com/archives/equities/mto/MTO_{ddmmyyyy}.DAT"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
REQUEST_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class DeliveryRecord:
    symbol: str
    series: str
    traded_qty: int
    delivery_qty: int
    delivery_pct: float


@dataclass
class MtoFetchResult:
    trading_date: date
    found: bool
    records: list[DeliveryRecord] = field(default_factory=list)
    error: str | None = None


def fetch_mto_file(trading_date: date, session: requests.Session | None = None) -> MtoFetchResult:
    """Fetch and parse one day's NSE delivery-position report.

    Returns `found=False` (not an error) for non-trading days, which return HTTP 404 from NSE.
    """
    url = MTO_URL_TEMPLATE.format(ddmmyyyy=trading_date.strftime("%d%m%Y"))
    http = session or requests
    try:
        resp = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return MtoFetchResult(trading_date=trading_date, found=False, error=str(exc))

    if resp.status_code == 404:
        return MtoFetchResult(trading_date=trading_date, found=False)
    if resp.status_code != 200:
        return MtoFetchResult(
            trading_date=trading_date, found=False, error=f"HTTP {resp.status_code}"
        )

    return MtoFetchResult(
        trading_date=trading_date, found=True, records=parse_mto_content(resp.text)
    )


def parse_mto_content(content: str) -> list[DeliveryRecord]:
    """Parse raw MTO file text into delivery records, keeping only EQ-series rows.

    Rows with a non-numeric delivery percentage (NSE writes "-" for some series when delivery
    is not applicable) are skipped rather than coerced to 0.0 - unmeasurable is not zero.
    """
    records: list[DeliveryRecord] = []
    for line in content.splitlines():
        if not line.startswith("20,"):
            continue
        fields = [f.strip() for f in line.split(",")]
        if len(fields) < 7:
            continue
        _, _sr_no, symbol, series, traded_qty_s, delivery_qty_s, delivery_pct_s = fields[:7]
        if series != "EQ":
            continue
        try:
            traded_qty = int(traded_qty_s)
            delivery_qty = int(delivery_qty_s)
            delivery_pct = float(delivery_pct_s)
        except ValueError:
            continue
        records.append(
            DeliveryRecord(
                symbol=symbol,
                series=series,
                traded_qty=traded_qty,
                delivery_qty=delivery_qty,
                delivery_pct=delivery_pct,
            )
        )
    return records
