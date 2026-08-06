"""Single-store enforcement and database provenance stamping.

WHY THIS MODULE EXISTS
======================
The project ran on TWO databases that never cross-checked each other:

    CLI (data backfill / update / verify)  ->  postgresql://localhost:5432/tradecraft
    Research runners (scratch/run_m3*.py)  ->  sqlite:///data/tradecraft.db

`SessionLocal` builds a PostgreSQL URL from `.env`, but twelve research runners called
`create_engine("sqlite:///.../data/tradecraft.db")` directly. Every Cycle 1 and Cycle 2
backtest read the SQLite file; every ingestion command wrote to PostgreSQL. Neither store
knew about the other, and no result artifact recorded which one it came from.

Worse, several runners performed a "preflight integrity check" that asserted a hardcoded
SHA-256 of the SQLite file:

    expected_db_sha = "6d336dcdf1e1a0454ca53a56861ada387f24e70c9aa476b74081c8014c81f28f"
    if compute_sha256(db_path) != expected_db_sha:
        raise RuntimeError("PREFLIGHT DATABASE CHECKSUM FAILURE")

That check was presented as tamper-evidence. In practice it PINNED THE SYNTHETIC DATABASE
IN PLACE: any attempt to ingest real market data would change the file hash and cause the
runner to refuse to start. An integrity control was preventing the correction of a data
integrity failure.

WHAT THIS MODULE ENFORCES
=========================
1. One store. Research code resolves its session through `resolve_research_session()`, which
   uses the same configured database as the CLI. Hardcoded file paths are rejected.
2. Provenance on every artifact. `fingerprint()` returns an identity record for the database
   actually used, so a result can always be traced to its source. Content is described by
   observable statistics, never by a pinned hash that forbids the data from changing.

See docs/research/REPO_AUDIT_2026-08-06.md.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from tradecraft.config import settings
from tradecraft.core.db import SessionLocal

logger = logging.getLogger("tradecraft.db_provenance")


class DatabaseStoreError(RuntimeError):
    """Raised when research code attempts to bypass the configured single store."""


# Paths that must never be opened directly by research code.
_FORBIDDEN_PATH_PATTERNS = (
    re.compile(r"sqlite:.*tradecraft\.db", re.IGNORECASE),
    re.compile(r"sqlite:///[a-z]:[\\/]", re.IGNORECASE),  # absolute Windows sqlite paths
)


def redact_url(url: str) -> str:
    """Strip credentials from a SQLAlchemy URL so it is safe to log or persist."""
    return re.sub(r"://([^:/@]+):([^@]*)@", r"://\1:***@", url)


def guard_no_hardcoded_store(url: str) -> None:
    """Reject a database URL that bypasses the configured store.

    Research code must not choose its own database. Doing so is what allowed ingestion and
    backtesting to diverge for two research cycles without anyone noticing.
    """
    for pattern in _FORBIDDEN_PATH_PATTERNS:
        if pattern.search(url):
            raise DatabaseStoreError(
                f"Hardcoded database path rejected: {redact_url(url)}\n\n"
                "Research code must resolve its session through "
                "tradecraft.core.db_provenance.resolve_research_session(), which uses the "
                "same store as the CLI. Twelve runners previously hardcoded "
                "sqlite:///data/tradecraft.db while ingestion wrote to PostgreSQL, so every "
                "backtest read a database that no ingestion ever updated.\n"
                "See docs/research/REPO_AUDIT_2026-08-06.md"
            )


def resolve_research_session() -> Session:
    """Return a session on the single configured research store.

    This is the ONLY sanctioned way for research code to obtain a database session.
    """
    url = settings.database_url
    guard_no_hardcoded_store(url)
    logger.info("Research session resolved to %s", redact_url(url))
    return SessionLocal()


@dataclass(frozen=True)
class DatabaseFingerprint:
    """Identity and content summary of the database a result was derived from.

    Deliberately describes content by observable statistics rather than by a pinned file
    hash. A hash lock cannot distinguish "the data was tampered with" from "the data was
    finally corrected", and in this repository it enforced the latter.
    """

    resolved_at: str
    database_url_redacted: str
    dialect: str
    host: str | None
    database_name: str | None
    instrument_count: int
    bar_count: int
    earliest_bar: str | None
    latest_bar: str | None
    distinct_instruments_with_bars: int
    sources: dict[str, int] = field(default_factory=dict)
    authenticity_gate_passed: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self) -> str:
        lines = [
            "DATA PROVENANCE",
            f"  store        : {self.dialect} {self.database_url_redacted}",
            f"  database     : {self.database_name}",
            f"  instruments  : {self.instrument_count} "
            f"({self.distinct_instruments_with_bars} with bars)",
            f"  bars         : {self.bar_count}",
            f"  range        : {self.earliest_bar} -> {self.latest_bar}",
            f"  sources      : {self.sources}",
            f"  authenticity : {self.authenticity_gate_passed}",
            f"  resolved_at  : {self.resolved_at}",
        ]
        return "\n".join(lines)


def fingerprint(session: Session, run_authenticity_gate: bool = False) -> DatabaseFingerprint:
    """Build a provenance record for the database behind `session`.

    Args:
        run_authenticity_gate: When True, also runs the data authenticity gate and records
            the verdict. Costs a full table scan, so it is opt-in.
    """
    bind = session.get_bind()
    url = bind.url if bind is not None else None

    dialect = url.get_backend_name() if url is not None else "unknown"
    host = url.host if url is not None else None
    db_name = url.database if url is not None else None
    url_str = redact_url(str(url)) if url is not None else "unknown"

    def _scalar(sql: str, default: Any = 0) -> Any:
        try:
            return session.execute(text(sql)).scalar() or default
        except Exception:  # table may not exist yet
            return default

    instrument_count = int(_scalar("SELECT COUNT(*) FROM instruments"))
    bar_count = int(_scalar("SELECT COUNT(*) FROM market_bars"))
    distinct = int(_scalar("SELECT COUNT(DISTINCT instrument_id) FROM market_bars"))
    earliest = _scalar("SELECT MIN(trading_date) FROM market_bars", None)
    latest = _scalar("SELECT MAX(trading_date) FROM market_bars", None)

    sources: dict[str, int] = {}
    try:
        for row in session.execute(
            text("SELECT source, COUNT(*) AS n FROM market_bars GROUP BY source")
        ):
            sources[str(row[0])] = int(row[1])
    except Exception:
        pass

    gate_passed: bool | None = None
    if run_authenticity_gate:
        try:
            from tradecraft.market_data.authenticity import DataAuthenticityGate

            gate_passed = DataAuthenticityGate().run(session).passed
        except Exception as e:  # never let provenance capture break a run
            logger.warning("Authenticity gate could not be evaluated: %s", e)

    def _iso(v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return str(v)[:10]

    return DatabaseFingerprint(
        resolved_at=datetime.now(timezone.utc).isoformat(),
        database_url_redacted=url_str,
        dialect=dialect,
        host=host,
        database_name=db_name,
        instrument_count=instrument_count,
        bar_count=bar_count,
        earliest_bar=_iso(earliest),
        latest_bar=_iso(latest),
        distinct_instruments_with_bars=distinct,
        sources=sources,
        authenticity_gate_passed=gate_passed,
    )
