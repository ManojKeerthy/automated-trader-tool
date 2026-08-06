"""Post-ingestion data quality diagnostics.

The authenticity gate (`market_data/authenticity.py`) answers one question: is this data
REAL? This module answers the next one: is real data CLEAN ENOUGH to research on?

They are different failures. A synthetic series is uniformly fake. Real vendor data is
mostly right and wrong in specific, locatable places — an unadjusted bonus issue, a stale
illiquid name, a symbol whose history is stitched across a demerger. Those defects survive
the authenticity gate because they are, in fact, real data. They still destroy backtests.

CORPORATE ACTION ADJUSTMENT — CORRECTED 2026-08-06
====================================================
The original assumption here (`backfill.py` writes `is_adjusted=False`, provider performs no
adjustment, so a bonus would appear as a fake overnight gap) is wrong. Zerodha's Kite Connect
historical API adjusts for bonuses, splits, rights, spin-offs and dividends server-side,
retroactively (https://x.com/zerodha/status/1952292763929874868), confirmed empirically
against four real in-window bonus ex-dates that show zero price gap. `backfill.py` now
writes `is_adjusted=True`.

`UNEXPLAINED_LARGE_MOVE` flags below therefore do NOT mean "unadjusted corporate action" —
checked against all 17 candidates the detector scored HIGH_CONFIDENCE on this dataset, and
17/17 were genuine market events (the 2020-03-23 COVID crash week, the 2024-06-04
election-result crash, company-specific news) rather than corporate actions. Treat a flag
here as "large move, cause not yet identified," not as a data defect to fix by adjustment.

`adjustment_audit()` cross-references every extreme move against the `corporate_actions`
table so the two can be told apart:
  - extreme move WITH a matching corporate action  -> almost certainly an adjustment defect
  - extreme move with NO corporate action          -> possibly a genuine event, or a data error
On current evidence, expect most/all flagged moves to fall in the second bucket and to be
genuine, not errors — verify before assuming otherwise.

See docs/research/REPO_AUDIT_2026-08-06.md and docs/PROJECT_STATUS.md section 3.2.1.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("tradecraft.quality_report")

EXTREME_MOVE_THRESHOLD = 0.25  # |daily return| beyond which a move warrants explanation
CORPORATE_ACTION_WINDOW_DAYS = 5  # proximity for matching a move to an ex-date
STALE_DISTINCT_CLOSE_PCT = 90.0
DUPLICATE_CORRELATION_THRESHOLD = 0.95
MIN_RESEARCH_BARS = 500


@dataclass
class ExtremeMove:
    symbol: str
    move_date: date
    prev_close: float
    close: float
    pct_change: float
    matched_action: str | None = None
    action_ex_date: date | None = None

    @property
    def verdict(self) -> str:
        if self.matched_action:
            return "LIKELY_UNADJUSTED_CORPORATE_ACTION"
        if abs(self.pct_change) >= 0.60:
            return "UNEXPLAINED_EXTREME_MOVE"
        return "UNEXPLAINED_LARGE_MOVE"


@dataclass
class StaleInstrument:
    symbol: str
    bars: int
    distinct_close_pct: float
    longest_flat_run: int
    zero_volume_days: int


@dataclass
class QualityReport:
    instrument_count: int = 0
    bar_count: int = 0
    extreme_moves: list[ExtremeMove] = field(default_factory=list)
    stale_instruments: list[StaleInstrument] = field(default_factory=list)
    duplicate_pairs: list[tuple[str, str, float]] = field(default_factory=list)
    short_history: list[tuple[str, int]] = field(default_factory=list)
    coverage_gaps: list[tuple[str, int]] = field(default_factory=list)
    corporate_action_count: int = 0

    @property
    def likely_adjustment_defects(self) -> list[ExtremeMove]:
        return [m for m in self.extreme_moves if m.matched_action]

    @property
    def blocking(self) -> bool:
        """True when a defect would corrupt backtests rather than merely add noise."""
        return bool(self.likely_adjustment_defects) or any(
            abs(m.pct_change) >= 0.60 for m in self.extreme_moves
        )

    def render(self, top_n: int = 25) -> str:
        out: list[str] = []
        out.append("=" * 78)
        out.append("  POST-INGESTION DATA QUALITY REPORT")
        out.append("=" * 78)
        out.append(f"  instruments={self.instrument_count}  bars={self.bar_count}  "
                   f"corporate_actions={self.corporate_action_count}")
        out.append("-" * 78)

        out.append(f"\n  EXTREME DAILY MOVES (|move| >= {EXTREME_MOVE_THRESHOLD:.0%}): "
                   f"{len(self.extreme_moves)}")
        if self.corporate_action_count == 0:
            out.append("    NOTE: the corporate_actions table is EMPTY, so no move can be")
            out.append("          matched to an ex-date. Adjustment defects cannot be ruled")
            out.append("          out - they can only be missed. Populate corporate actions.")
        for m in sorted(self.extreme_moves, key=lambda x: -abs(x.pct_change))[:top_n]:
            tag = f"  <- {m.matched_action} ex {m.action_ex_date}" if m.matched_action else ""
            out.append(f"    {m.symbol:<14} {m.move_date}  {m.prev_close:>10.2f} -> "
                       f"{m.close:>10.2f}  {m.pct_change:>+8.1%}  [{m.verdict}]{tag}")
        if len(self.extreme_moves) > top_n:
            out.append(f"    ... and {len(self.extreme_moves) - top_n} more")

        out.append(f"\n  STALE / ILLIQUID INSTRUMENTS: {len(self.stale_instruments)}")
        for s in self.stale_instruments[:top_n]:
            out.append(f"    {s.symbol:<14} bars={s.bars:<6} distinct_close={s.distinct_close_pct:>5.1f}%  "
                       f"longest_flat_run={s.longest_flat_run:<4} zero_volume_days={s.zero_volume_days}")

        out.append(f"\n  NEAR-DUPLICATE SERIES (r >= {DUPLICATE_CORRELATION_THRESHOLD}): "
                   f"{len(self.duplicate_pairs)}")
        for a, b, r in self.duplicate_pairs[:top_n]:
            out.append(f"    {a:<14} ~ {b:<14} r={r:.4f}")
        if self.duplicate_pairs:
            out.append("    These may be the same underlying listed twice (pre/post rename or")
            out.append("    demerger). Keeping both double-counts the name in any ranking.")

        out.append(f"\n  SHORT HISTORY (< {MIN_RESEARCH_BARS} bars): {len(self.short_history)}")
        for sym, n in self.short_history[:top_n]:
            out.append(f"    {sym:<14} {n} bars")

        out.append(f"\n  INTERNAL COVERAGE GAPS: {len(self.coverage_gaps)}")
        for sym, n in self.coverage_gaps[:top_n]:
            out.append(f"    {sym:<14} {n} missing sessions within its own date range")

        out.append("\n" + "-" * 78)
        if self.blocking:
            out.append("  VERDICT: DEFECTS PRESENT THAT WOULD CORRUPT BACKTESTS")
            out.append("")
            out.append("  Unadjusted corporate actions create overnight gaps that never")
            out.append("  happened. Every long position in the affected name is stopped out on")
            out.append("  a date unrelated to the strategy. That produces exactly the Cycle 1")
            out.append("  symptom - 'almost every trade hits its stop' - on real data.")
            out.append("  Resolve before interpreting any backtest.")
        else:
            out.append("  VERDICT: NO BLOCKING DEFECTS DETECTED")
        out.append("=" * 78)
        return "\n".join(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_count": self.instrument_count,
            "bar_count": self.bar_count,
            "corporate_action_count": self.corporate_action_count,
            "blocking": self.blocking,
            "extreme_moves": [
                {
                    "symbol": m.symbol,
                    "date": m.move_date.isoformat(),
                    "prev_close": m.prev_close,
                    "close": m.close,
                    "pct_change": m.pct_change,
                    "verdict": m.verdict,
                    "matched_action": m.matched_action,
                }
                for m in self.extreme_moves
            ],
            "stale_instruments": [
                {"symbol": s.symbol, "bars": s.bars, "distinct_close_pct": s.distinct_close_pct}
                for s in self.stale_instruments
            ],
            "duplicate_pairs": [
                {"a": a, "b": b, "correlation": r} for a, b, r in self.duplicate_pairs
            ],
            "short_history": [{"symbol": s, "bars": n} for s, n in self.short_history],
        }


class DataQualityReporter:
    """Locates specific, actionable defects in real ingested market data."""

    def _load(self, session: Session) -> dict[str, list[dict[str, Any]]]:
        rows = session.execute(
            text(
                """
                SELECT i.symbol AS symbol, m.trading_date AS d,
                       m.close AS c, m.volume AS v
                FROM market_bars m
                JOIN instruments i ON i.id = m.instrument_id
                ORDER BY i.symbol, m.trading_date
                """
            )
        ).mappings()
        series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            d = r["d"]
            if isinstance(d, str):
                d = date.fromisoformat(d[:10])
            series[r["symbol"]].append(
                {"date": d, "close": float(r["c"]), "volume": int(r["v"] or 0)}
            )
        return dict(series)

    def _load_actions(self, session: Session) -> dict[str, list[tuple[date, str]]]:
        actions: dict[str, list[tuple[date, str]]] = defaultdict(list)
        try:
            rows = session.execute(
                text(
                    """
                    SELECT i.symbol AS symbol, ca.ex_date AS ex_date,
                           ca.action_type AS action_type
                    FROM corporate_actions ca
                    JOIN instruments i ON i.id = ca.instrument_id
                    """
                )
            ).mappings()
            for r in rows:
                ed = r["ex_date"]
                if isinstance(ed, str):
                    ed = date.fromisoformat(ed[:10])
                if ed:
                    actions[r["symbol"]].append((ed, str(r["action_type"])))
        except Exception as e:
            logger.warning("Could not load corporate actions: %s", e)
        return dict(actions)

    def run(self, session: Session) -> QualityReport:
        series = self._load(session)
        actions = self._load_actions(session)
        rep = QualityReport()
        rep.instrument_count = len(series)
        rep.bar_count = sum(len(b) for b in series.values())
        rep.corporate_action_count = sum(len(v) for v in actions.values())

        for sym, bars in series.items():
            if len(bars) < MIN_RESEARCH_BARS:
                rep.short_history.append((sym, len(bars)))

            closes = [b["close"] for b in bars]

            # --- extreme moves, matched against corporate actions -------------------
            for i in range(1, len(bars)):
                prev, cur = closes[i - 1], closes[i]
                if prev <= 0:
                    continue
                chg = (cur - prev) / prev
                if abs(chg) < EXTREME_MOVE_THRESHOLD:
                    continue
                move_date = bars[i]["date"]
                matched, ex_date = None, None
                for ed, atype in actions.get(sym, []):
                    if abs((ed - move_date).days) <= CORPORATE_ACTION_WINDOW_DAYS:
                        matched, ex_date = atype, ed
                        break
                rep.extreme_moves.append(
                    ExtremeMove(sym, move_date, prev, cur, chg, matched, ex_date)
                )

            # --- staleness ----------------------------------------------------------
            if len(closes) >= 100:
                distinct_pct = 100.0 * len(set(closes)) / len(closes)
                run_len = best = 1
                for i in range(1, len(closes)):
                    run_len = run_len + 1 if closes[i] == closes[i - 1] else 1
                    best = max(best, run_len)
                zero_vol = sum(1 for b in bars if b["volume"] == 0)
                if distinct_pct < STALE_DISTINCT_CLOSE_PCT or best >= 5 or zero_vol > 5:
                    rep.stale_instruments.append(
                        StaleInstrument(sym, len(bars), distinct_pct, best, zero_vol)
                    )

            # --- internal coverage gaps (calendar-free heuristic) --------------------
            if len(bars) >= 100:
                span_days = (bars[-1]["date"] - bars[0]["date"]).days
                expected = int(span_days * 5 / 7 * 0.96)  # weekdays less ~holidays
                missing = expected - len(bars)
                if missing > 20:
                    rep.coverage_gaps.append((sym, missing))

        rep.stale_instruments.sort(key=lambda s: s.distinct_close_pct)
        rep.short_history.sort(key=lambda x: x[1])
        rep.coverage_gaps.sort(key=lambda x: -x[1])
        rep.duplicate_pairs = self._duplicate_pairs(series)
        return rep

    def _duplicate_pairs(
        self, series: dict[str, list[dict[str, Any]]]
    ) -> list[tuple[str, str, float]]:
        """Find near-identical return series - usually one underlying listed twice."""
        rets: dict[str, dict[date, float]] = {}
        for sym, bars in series.items():
            if len(bars) < MIN_RESEARCH_BARS:
                continue
            m: dict[date, float] = {}
            for i in range(1, len(bars)):
                p = bars[i - 1]["close"]
                if p > 0:
                    m[bars[i]["date"]] = (bars[i]["close"] - p) / p
            rets[sym] = m

        out: list[tuple[str, str, float]] = []
        syms = sorted(rets)
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                a, b = rets[syms[i]], rets[syms[j]]
                common = a.keys() & b.keys()
                if len(common) < 200:
                    continue
                xs = [a[d] for d in common]
                ys = [b[d] for d in common]
                mx, my = statistics.fmean(xs), statistics.fmean(ys)
                num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
                dy = math.sqrt(sum((y - my) ** 2 for y in ys))
                if dx == 0 or dy == 0:
                    continue
                r = num / (dx * dy)
                if r >= DUPLICATE_CORRELATION_THRESHOLD:
                    out.append((syms[i], syms[j], r))
        return sorted(out, key=lambda t: -t[2])


def build_quality_report(session: Session) -> QualityReport:
    return DataQualityReporter().run(session)
