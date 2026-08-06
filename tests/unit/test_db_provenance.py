"""Single-store enforcement and provenance stamping tests.

Guards the defect where ingestion wrote to PostgreSQL while every research runner read a
stale `sqlite:///data/tradecraft.db`, and no result artifact recorded which store it came
from. See docs/research/REPO_AUDIT_2026-08-06.md.
"""

from __future__ import annotations

import ast
import glob
import os
import re

import pytest

from tradecraft.core.db_provenance import (
    DatabaseStoreError,
    guard_no_hardcoded_store,
    redact_url,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSingleStoreGuard:
    @pytest.mark.parametrize(
        "url",
        [
            "sqlite:///data/tradecraft.db",
            "sqlite:///c:/infiligence/automated-trader-tool/data/tradecraft.db",
            "sqlite:////home/user/tradecraft.db",
            "SQLite:///DATA/TRADECRAFT.DB",
        ],
    )
    def test_hardcoded_research_store_is_rejected(self, url: str) -> None:
        with pytest.raises(DatabaseStoreError):
            guard_no_hardcoded_store(url)

    @pytest.mark.parametrize(
        "url",
        [
            "postgresql://tradecraft:secret@localhost:5432/tradecraft",
            "postgresql+psycopg://u:p@db.internal:5432/tradecraft",
        ],
    )
    def test_configured_store_is_allowed(self, url: str) -> None:
        guard_no_hardcoded_store(url)

    def test_error_message_is_actionable(self) -> None:
        with pytest.raises(DatabaseStoreError) as exc:
            guard_no_hardcoded_store("sqlite:///data/tradecraft.db")
        msg = str(exc.value)
        assert "resolve_research_session" in msg
        assert "REPO_AUDIT" in msg

    def test_in_memory_sqlite_still_allowed_for_tests(self) -> None:
        """Unit tests legitimately use in-memory SQLite; only file stores are blocked."""
        guard_no_hardcoded_store("sqlite:///:memory:")


class TestCredentialRedaction:
    def test_password_is_redacted(self) -> None:
        out = redact_url("postgresql://tradecraft:hunter2@localhost:5432/tradecraft")
        assert "hunter2" not in out
        assert "***" in out
        assert "tradecraft" in out and "localhost:5432" in out

    def test_urls_without_credentials_are_unchanged(self) -> None:
        assert redact_url("sqlite:///:memory:") == "sqlite:///:memory:"

    def test_fingerprint_never_persists_a_password(self) -> None:
        from tradecraft.core.db_provenance import DatabaseFingerprint

        fp = DatabaseFingerprint(
            resolved_at="2026-08-06T00:00:00+00:00",
            database_url_redacted=redact_url("postgresql://u:topsecret@h:5432/db"),
            dialect="postgresql",
            host="h",
            database_name="db",
            instrument_count=100,
            bar_count=250000,
            earliest_bar="2015-01-01",
            latest_bar="2026-08-05",
            distinct_instruments_with_bars=100,
        )
        assert "topsecret" not in str(fp.to_dict())
        assert "topsecret" not in fp.render()


class TestNoRunnerRegressesToAHardcodedStore:
    """Static scan. The repointing must not quietly come undone."""

    @staticmethod
    def _runner_files() -> list[str]:
        files = glob.glob(os.path.join(REPO_ROOT, "scratch", "run_*.py"))
        files += glob.glob(os.path.join(REPO_ROOT, "scratch", "audit_*.py"))
        # The synthetic fixture generator legitimately writes to its own guarded SQLite path.
        return [f for f in files if "generate_synthetic_fixture" not in f]

    def test_no_runner_calls_create_engine_on_a_sqlite_file(self) -> None:
        offenders = []
        for f in self._runner_files():
            src = open(f, encoding="utf-8").read()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "create_engine":
                    for arg in node.args:
                        literal = ast.dump(arg)
                        if "sqlite" in literal.lower():
                            offenders.append(f"{os.path.basename(f)}:{node.lineno}")
        assert not offenders, (
            "Research runners must resolve the configured store via "
            f"resolve_research_session(), not open a file directly: {offenders}"
        )

    def test_no_runner_pins_a_database_checksum(self) -> None:
        """A pinned SHA-256 of the data file blocks correcting the data.

        The original preflight asserted a hardcoded hash of the synthetic SQLite file, so
        ingesting real market data would have raised PREFLIGHT DATABASE CHECKSUM FAILURE.
        An integrity control was preventing an integrity fix.
        """
        offenders = []
        pattern = re.compile(r'expected_db_sha\s*=\s*["\'][0-9a-f]{64}["\']')
        for f in self._runner_files():
            src = open(f, encoding="utf-8").read()
            if pattern.search(src):
                offenders.append(os.path.basename(f))
        assert not offenders, f"Runners pin a database checksum: {offenders}"


class TestResultCarriesProvenance:
    def test_backtest_result_has_a_provenance_field(self) -> None:
        from tradecraft.backtesting.engine import BacktestResult

        assert "data_provenance" in BacktestResult.__dataclass_fields__

    def test_provenance_defaults_to_empty_not_missing(self) -> None:
        import dataclasses

        from tradecraft.backtesting.engine import BacktestResult

        f = BacktestResult.__dataclass_fields__["data_provenance"]
        assert f.default_factory is not dataclasses.MISSING
