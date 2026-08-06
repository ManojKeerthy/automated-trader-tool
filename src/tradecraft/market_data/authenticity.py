"""Data Authenticity Gate — adversarial verification that market data is REAL.

WHY THIS MODULE EXISTS
======================
Research Cycles 1 and 2 were conducted entirely against a synthetic price database
(`scratch/seed_real_market_bars.py`) whose bars were stamped `source = "ZERODHA_KITE_EOD"`.
Two full research cycles, ~250 governance documents, SHA-256 database certificates and an
"Authenticity Guarantee" all passed, because every existing control verified INTERNAL
CONSISTENCY (did the number in the report come from the database?) and none verified
EXTERNAL VALIDITY (do these prices resemble the NSE?).

See docs/research/REPO_AUDIT_2026-08-06.md.

DESIGN PRINCIPLE
================
This gate is ADVERSARIAL. It does not ask "does this look plausible?" — it asks
"what would a fabricated series fail?" Every check below is one the known synthetic
generator fails outright. Provenance is a property of the numbers, never of the
`source` string column, which any generator can write.

The gate is deliberately conservative: it is designed to have effectively zero false
positives on real NSE daily equity data, so that a FAIL is always actionable.

USAGE
=====
    from tradecraft.market_data.authenticity import DataAuthenticityGate

    report = DataAuthenticityGate().run(session)
    if not report.passed:
        raise DataAuthenticityError(report.render())

Enforced as a blocking precondition in `tradecraft.core.preflight.validate_research_data`.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("tradecraft.authenticity")

GATE_VERSION = "1.0.0"

# --------------------------------------------------------------------------------------
# Thresholds. Deliberately loose — these are designed to catch fabrication, not to
# characterise market microstructure. Real NSE large-cap data clears every one of them
# with wide margin; the known synthetic generator fails six of them outright.
# --------------------------------------------------------------------------------------

MIN_INSTRUMENTS = 20
MIN_BARS_PER_INSTRUMENT = 500
MAX_MEAN_PAIRWISE_CORRELATION = 0.90
MIN_VOL_DISPERSION_PCT = 3.0
MIN_OPEN_NE_CLOSE_PCT = 95.0
MIN_HL_RATIO_STDEV = 0.002
MIN_ABS_DAILY_MOVE_TAIL = 0.06
MIN_TAIL_DAYS = 5
MIN_KURTOSIS = 1.0
MAX_VOLUME_MONOTONIC_PCT = 70.0
MIN_VOLUME_CV = 0.20
MIN_DISTINCT_CLOSE_PCT = 90.0

# Known historical stress windows. If a dataset spans one of these, real Indian equities
# MUST show a large drawdown inside it. A generator with bounded returns cannot.
KNOWN_STRESS_WINDOWS: list[tuple[str, date, date, float]] = [
    ("COVID-19 crash", date(2020, 2, 1), date(2020, 4, 30), 0.25),
    ("2016 demonetisation", date(2016, 11, 1), date(2016, 12, 31), 0.06),
    ("2018 IL&FS / NBFC crisis", date(2018, 8, 15), date(2018, 10, 31), 0.10),
]

# Any bar carrying one of these source stamps is fabricated by definition.
FORBIDDEN_SOURCES = {"SYNTHETIC_FIXTURE", "MOCK", "FAKE", "TEST_FIXTURE", "GENERATED"}


class DataAuthenticityError(RuntimeError):
    """Raised when a research database fails the data authenticity gate."""


@dataclass
class CheckResult:
    """Outcome of a single authenticity check."""

    name: str
    passed: bool
    observed: str
    expected: str
    rationale: str
    severity: str = "BLOCKING"  # BLOCKING | WARNING

    @property
    def symbol(self) -> str:
        if self.passed:
            return "PASS"
        return "FAIL" if self.severity == "BLOCKING" else "WARN"


@dataclass
class AuthenticityReport:
    """Full result of a data authenticity run."""

    gate_version: str
    checks: list[CheckResult] = field(default_factory=list)
    instrument_count: int = 0
    bar_count: int = 0
    date_range: tuple[date | None, date | None] = (None, None)
    skipped: list[str] = field(default_factory=list)

    @property
    def blocking_failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "BLOCKING"]

    @property
    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "WARNING"]

    @property
    def passed(self) -> bool:
        return not self.blocking_failures

    def render(self) -> str:
        """Human-readable report suitable for an exception message or CLI output."""
        lines: list[str] = []
        lines.append("=" * 78)
        verdict = "DATA_AUTHENTICITY_PASSED" if self.passed else "DATA_AUTHENTICITY_FAILED"
        lines.append(f"  {verdict}   (gate v{self.gate_version})")
        lines.append("=" * 78)
        start, end = self.date_range
        lines.append(
            f"  instruments={self.instrument_count}  bars={self.bar_count}  "
            f"range={start} -> {end}"
        )
        lines.append("-" * 78)
        for c in self.checks:
            lines.append(f"  [{c.symbol}] {c.name}")
            lines.append(f"         observed: {c.observed}")
            lines.append(f"         expected: {c.expected}")
            if not c.passed:
                lines.append(f"         why:      {c.rationale}")
        for s in self.skipped:
            lines.append(f"  [SKIP] {s}")
        lines.append("-" * 78)
        if not self.passed:
            lines.append("")
            lines.append("  THIS DATABASE DOES NOT CONTAIN REAL MARKET DATA.")
            lines.append("  Backtesting against it produces meaningless results.")
            lines.append("")
            lines.append("  Ingest real NSE data:")
            lines.append(
                "      python -m tradecraft data backfill --universe NIFTY100 "
                "--start 2015-01-01"
            )
            lines.append("")
            lines.append("  Background: docs/research/REPO_AUDIT_2026-08-06.md")
        lines.append("=" * 78)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        start, end = self.date_range
        return {
            "gate_version": self.gate_version,
            "passed": self.passed,
            "instrument_count": self.instrument_count,
            "bar_count": self.bar_count,
            "date_range": [start.isoformat() if start else None, end.isoformat() if end else None],
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "observed": c.observed,
                    "expected": c.expected,
                    "severity": c.severity,
                }
                for c in self.checks
            ],
            "skipped": self.skipped,
        }


class DataAuthenticityGate:
    """Adversarial verification that a market database contains real price data."""

    def __init__(self, gate_version: str = GATE_VERSION) -> None:
        self.gate_version = gate_version

    # ---------------------------------------------------------------- data loading

    def _load(self, session: Session) -> dict[str, list[dict[str, Any]]]:
        """Load all bars grouped by symbol, ordered by date."""
        rows = session.execute(
            text(
                """
                SELECT i.symbol   AS symbol,
                       m.trading_date AS trading_date,
                       m.open  AS o,
                       m.high  AS h,
                       m.low   AS lo,
                       m.close AS c,
                       m.volume AS v,
                       m.source AS src
                FROM market_bars m
                JOIN instruments i ON i.id = m.instrument_id
                ORDER BY i.symbol, m.trading_date
                """
            )
        ).mappings()

        series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            td = r["trading_date"]
            if isinstance(td, str):
                td = date.fromisoformat(td[:10])
            series[r["symbol"]].append(
                {
                    "date": td,
                    "open": float(r["o"]),
                    "high": float(r["h"]),
                    "low": float(r["lo"]),
                    "close": float(r["c"]),
                    "volume": int(r["v"] or 0),
                    "source": r["src"],
                }
            )
        return dict(series)

    # ---------------------------------------------------------------- entry point

    def run(self, session: Session) -> AuthenticityReport:
        """Execute all authenticity checks against the database."""
        series = self._load(session)
        report = AuthenticityReport(gate_version=self.gate_version)

        if not series:
            report.checks.append(
                CheckResult(
                    name="database_populated",
                    passed=False,
                    observed="0 bars",
                    expected=f">= {MIN_BARS_PER_INSTRUMENT} bars per instrument",
                    rationale="The market_bars table is empty. Run the backfill first.",
                )
            )
            return report

        usable = {s: b for s, b in series.items() if len(b) >= MIN_BARS_PER_INSTRUMENT}
        report.instrument_count = len(series)
        report.bar_count = sum(len(b) for b in series.values())
        all_dates = [b["date"] for bars in series.values() for b in bars]
        report.date_range = (min(all_dates), max(all_dates))

        self._check_forbidden_sources(series, report)
        self._check_universe_size(series, usable, report)

        if not usable:
            report.skipped.append(
                "Statistical checks skipped: no instrument has "
                f">= {MIN_BARS_PER_INSTRUMENT} bars."
            )
            return report

        returns = {s: self._returns(b) for s, b in usable.items()}

        self._check_cross_sectional_correlation(returns, report)
        self._check_volatility_dispersion(returns, report)
        self._check_open_close_distinct(usable, report)
        self._check_intrabar_range_varies(usable, report)
        self._check_fat_tails(returns, report)
        self._check_return_kurtosis(returns, report)
        self._check_volume_realism(usable, report)
        self._check_price_granularity(usable, report)
        self._check_known_stress_windows(usable, report)

        return report

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _returns(bars: list[dict[str, Any]]) -> list[float]:
        out: list[float] = []
        for i in range(1, len(bars)):
            prev = bars[i - 1]["close"]
            if prev > 0:
                out.append((bars[i]["close"] - prev) / prev)
        return out

    @staticmethod
    def _pearson(a: list[float], b: list[float]) -> float | None:
        n = min(len(a), len(b))
        if n < 30:
            return None
        a, b = a[-n:], b[-n:]
        ma, mb = statistics.fmean(a), statistics.fmean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = math.sqrt(sum((x - ma) ** 2 for x in a))
        db = math.sqrt(sum((y - mb) ** 2 for y in b))
        if da == 0 or db == 0:
            return None
        return num / (da * db)

    # ---------------------------------------------------------------- checks

    def _check_forbidden_sources(
        self, series: dict[str, list[dict[str, Any]]], report: AuthenticityReport
    ) -> None:
        found = {
            b["source"]
            for bars in series.values()
            for b in bars
            if b["source"] and str(b["source"]).upper() in FORBIDDEN_SOURCES
        }
        report.checks.append(
            CheckResult(
                name="no_synthetic_source_stamps",
                passed=not found,
                observed=f"forbidden sources present: {sorted(found)}" if found else "none",
                expected=f"no bars stamped {sorted(FORBIDDEN_SOURCES)}",
                rationale=(
                    "Bars explicitly stamped as fixtures are present in a research database. "
                    "Note this check is necessary but NOT sufficient — the original synthetic "
                    "seeder stamped ZERODHA_KITE_EOD, which is why the statistical checks below "
                    "exist."
                ),
            )
        )

    def _check_universe_size(
        self,
        series: dict[str, list[dict[str, Any]]],
        usable: dict[str, list[dict[str, Any]]],
        report: AuthenticityReport,
    ) -> None:
        report.checks.append(
            CheckResult(
                name="universe_size",
                passed=len(usable) >= MIN_INSTRUMENTS,
                observed=f"{len(usable)} instruments with >= {MIN_BARS_PER_INSTRUMENT} bars "
                f"({len(series)} total)",
                expected=f">= {MIN_INSTRUMENTS} instruments",
                rationale=(
                    "Cross-sectional research (ranking, relative strength, sector rotation) "
                    "requires a cross-section. A handful of names cannot support it, and small "
                    "universes make survivorship bias dominant."
                ),
            )
        )

    def _check_cross_sectional_correlation(
        self, returns: dict[str, list[float]], report: AuthenticityReport
    ) -> None:
        """THE headline check. The synthetic generator produced correlation = 1.0."""
        syms = sorted(returns)
        corrs: list[float] = []
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                c = self._pearson(returns[syms[i]], returns[syms[j]])
                if c is not None:
                    corrs.append(c)

        if not corrs:
            report.skipped.append("cross_sectional_correlation: insufficient overlapping history")
            return

        mean_c = statistics.fmean(corrs)
        report.checks.append(
            CheckResult(
                name="cross_sectional_correlation",
                passed=mean_c < MAX_MEAN_PAIRWISE_CORRELATION,
                observed=f"mean pairwise r = {mean_c:.4f} (max {max(corrs):.4f}, "
                f"{len(corrs)} pairs)",
                expected=f"mean pairwise r < {MAX_MEAN_PAIRWISE_CORRELATION}",
                rationale=(
                    "Real large caps co-move at roughly r = 0.3-0.6. Near-unity correlation "
                    "means every instrument shares one return series — the defining signature "
                    "of the synthetic generator, and it makes all cross-sectional ranking "
                    "research mathematically vacuous."
                ),
            )
        )

    def _check_volatility_dispersion(
        self, returns: dict[str, list[float]], report: AuthenticityReport
    ) -> None:
        vols = [statistics.pstdev(r) * math.sqrt(252) * 100 for r in returns.values() if len(r) > 30]
        if len(vols) < 2:
            report.skipped.append("volatility_dispersion: fewer than 2 usable instruments")
            return
        spread = max(vols) - min(vols)
        report.checks.append(
            CheckResult(
                name="volatility_dispersion",
                passed=spread >= MIN_VOL_DISPERSION_PCT,
                observed=f"annualised vol spans {min(vols):.1f}% - {max(vols):.1f}% "
                f"(spread {spread:.2f}pp)",
                expected=f"spread >= {MIN_VOL_DISPERSION_PCT}pp",
                rationale=(
                    "Different companies have different volatility. Identical vol across the "
                    "universe means one generator drove every series. The synthetic DB showed "
                    "29.2% for all 10 names, to one decimal place."
                ),
            )
        )

    def _check_open_close_distinct(
        self, series: dict[str, list[dict[str, Any]]], report: AuthenticityReport
    ) -> None:
        total = ne = 0
        for bars in series.values():
            for b in bars:
                total += 1
                if abs(b["open"] - b["close"]) > 1e-9:
                    ne += 1
        pct = 100.0 * ne / total if total else 0.0
        report.checks.append(
            CheckResult(
                name="open_differs_from_close",
                passed=pct >= MIN_OPEN_NE_CLOSE_PCT,
                observed=f"{pct:.2f}% of bars have open != close",
                expected=f">= {MIN_OPEN_NE_CLOSE_PCT}%",
                rationale=(
                    "The synthetic generator computed open as the midpoint of high and low, "
                    "making open == close on every bar. That erases overnight gaps entirely — "
                    "and this engine executes at the T+1 OPEN, so gap handling, gap-through-stop "
                    "fills and slippage were all completely untested."
                ),
            )
        )

    def _check_intrabar_range_varies(
        self, series: dict[str, list[dict[str, Any]]], report: AuthenticityReport
    ) -> None:
        ratios: list[float] = []
        for bars in series.values():
            for b in bars:
                if b["close"] > 0:
                    ratios.append((b["high"] - b["low"]) / b["close"])
        if len(ratios) < 100:
            report.skipped.append("intrabar_range_varies: too few bars")
            return
        sd = statistics.pstdev(ratios)
        report.checks.append(
            CheckResult(
                name="intrabar_range_varies",
                passed=sd >= MIN_HL_RATIO_STDEV,
                observed=f"stdev of (high-low)/close = {sd:.6f} "
                f"(mean {statistics.fmean(ratios):.4f})",
                expected=f"stdev >= {MIN_HL_RATIO_STDEV}",
                rationale=(
                    "A constant intraday range means constant ATR. In the synthetic DB the "
                    "range was fixed at 2.4% of price forever, so every 'ATR-based' stop was "
                    "silently a fixed-percentage stop and all volatility filters were inert."
                ),
            )
        )

    def _check_fat_tails(
        self, returns: dict[str, list[float]], report: AuthenticityReport
    ) -> None:
        extremes = sum(1 for r in returns.values() for x in r if abs(x) >= MIN_ABS_DAILY_MOVE_TAIL)
        biggest = max((abs(x) for r in returns.values() for x in r), default=0.0)
        report.checks.append(
            CheckResult(
                name="fat_tails_present",
                passed=extremes >= MIN_TAIL_DAYS,
                observed=f"{extremes} daily moves >= {MIN_ABS_DAILY_MOVE_TAIL:.0%} "
                f"(largest {biggest:.2%})",
                expected=f">= {MIN_TAIL_DAYS} such moves",
                rationale=(
                    "Indian equities gap on earnings, blocks, regulatory news and index "
                    "rebalances. A series with no tail events has bounded returns by "
                    "construction. The synthetic DB's largest move in 8 years was 3.1%."
                ),
            )
        )

    def _check_return_kurtosis(
        self, returns: dict[str, list[float]], report: AuthenticityReport
    ) -> None:
        pooled = [x for r in returns.values() for x in r]
        if len(pooled) < 500:
            report.skipped.append("return_kurtosis: too few observations")
            return
        m = statistics.fmean(pooled)
        sd = statistics.pstdev(pooled)
        if sd == 0:
            excess = -3.0
        else:
            excess = sum(((x - m) / sd) ** 4 for x in pooled) / len(pooled) - 3.0
        report.checks.append(
            CheckResult(
                name="return_kurtosis",
                passed=excess >= MIN_KURTOSIS,
                observed=f"excess kurtosis = {excess:.2f}",
                expected=f">= {MIN_KURTOSIS}",
                rationale=(
                    "Real daily equity returns are strongly leptokurtic (typically 3-10). "
                    "Values near or below zero indicate a bounded or uniform generator rather "
                    "than a market."
                ),
            )
        )

    def _check_volume_realism(
        self, series: dict[str, list[dict[str, Any]]], report: AuthenticityReport
    ) -> None:
        mono_flags: list[bool] = []
        cvs: list[float] = []
        for bars in series.values():
            vols = [b["volume"] for b in bars if b["volume"] > 0]
            if len(vols) < 50:
                continue
            rises = sum(1 for i in range(1, len(vols)) if vols[i] > vols[i - 1])
            mono_flags.append(100.0 * rises / (len(vols) - 1) > MAX_VOLUME_MONOTONIC_PCT)
            mean_v = statistics.fmean(vols)
            if mean_v > 0:
                cvs.append(statistics.pstdev(vols) / mean_v)

        if not cvs:
            report.skipped.append("volume_realism: no usable volume data")
            return

        mono_pct = 100.0 * sum(mono_flags) / len(mono_flags) if mono_flags else 0.0
        median_cv = statistics.median(cvs)
        report.checks.append(
            CheckResult(
                name="volume_realism",
                passed=(mono_pct < 50.0) and (median_cv >= MIN_VOLUME_CV),
                observed=f"{mono_pct:.0f}% of instruments have near-monotonic volume; "
                f"median coefficient of variation = {median_cv:.3f}",
                expected=f"< 50% monotonic and CV >= {MIN_VOLUME_CV}",
                rationale=(
                    "The synthetic DB used a linear counter for volume (500000, 500131, "
                    "500262, ...). Any RVOL, volume-expansion or liquidity filter tested "
                    "against that was measuring a ramp function, not participation."
                ),
            )
        )

    def _check_price_granularity(
        self, series: dict[str, list[dict[str, Any]]], report: AuthenticityReport
    ) -> None:
        pcts: list[float] = []
        for bars in series.values():
            closes = [b["close"] for b in bars]
            if len(closes) >= 100:
                pcts.append(100.0 * len(set(closes)) / len(closes))
        if not pcts:
            report.skipped.append("price_granularity: too few bars")
            return
        worst = min(pcts)
        report.checks.append(
            CheckResult(
                name="price_granularity",
                passed=worst >= MIN_DISTINCT_CLOSE_PCT,
                observed=f"lowest distinct-close ratio across instruments = {worst:.1f}%",
                expected=f">= {MIN_DISTINCT_CLOSE_PCT}%",
                rationale=(
                    "Heavy repetition of exact close prices suggests a small discrete "
                    "generator alphabet, a stale/forward-filled feed, or a halted instrument."
                ),
                severity="WARNING",
            )
        )

    def _check_known_stress_windows(
        self, series: dict[str, list[dict[str, Any]]], report: AuthenticityReport
    ) -> None:
        """Real markets crashed on known dates. A bounded generator cannot reproduce this."""
        for label, w_start, w_end, min_dd in KNOWN_STRESS_WINDOWS:
            covering = [
                bars
                for bars in series.values()
                if bars and bars[0]["date"] <= w_start and bars[-1]["date"] >= w_end
            ]
            if len(covering) < 5:
                report.skipped.append(
                    f"stress_window[{label}]: dataset does not span {w_start} -> {w_end}"
                )
                continue

            drawdowns: list[float] = []
            for bars in covering:
                window = [b["close"] for b in bars if w_start <= b["date"] <= w_end]
                if len(window) < 10:
                    continue
                peak = window[0]
                mdd = 0.0
                for c in window:
                    peak = max(peak, c)
                    if peak > 0:
                        mdd = max(mdd, (peak - c) / peak)
                drawdowns.append(mdd)

            if not drawdowns:
                report.skipped.append(f"stress_window[{label}]: insufficient bars in window")
                continue

            median_dd = statistics.median(drawdowns)
            report.checks.append(
                CheckResult(
                    name=f"stress_window[{label}]",
                    passed=median_dd >= min_dd,
                    observed=f"median drawdown {median_dd:.1%} across {len(drawdowns)} "
                    f"instruments ({w_start} -> {w_end})",
                    expected=f">= {min_dd:.0%}",
                    rationale=(
                        f"Indian equities fell sharply during {label}. Data spanning this "
                        "window without the drawdown is not a record of that market."
                    ),
                )
            )


def verify_data_authenticity(session: Session, raise_on_fail: bool = True) -> AuthenticityReport:
    """Run the gate and optionally raise. Convenience wrapper for CLI and preflight."""
    report = DataAuthenticityGate().run(session)
    if report.passed:
        logger.info("Data authenticity gate PASSED (v%s)", report.gate_version)
    else:
        logger.error("Data authenticity gate FAILED\n%s", report.render())
        if raise_on_fail:
            raise DataAuthenticityError(report.render())
    return report
