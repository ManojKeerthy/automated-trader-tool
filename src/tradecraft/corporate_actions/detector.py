"""Corporate action detection from price series.

CORRECTION, 2026-08-06 — READ BEFORE TRUSTING THIS MODULE'S OUTPUT
====================================================================
The premise below (unadjusted vendor feed => detect bonuses from price gaps) is WRONG for
this data source. Zerodha's Kite Connect historical API adjusts for bonuses, splits, rights
issues, spin-offs and extraordinary dividends server-side, retroactively, at the ex-date
(https://x.com/zerodha/status/1952292763929874868). `backfill.py` now writes
`is_adjusted=True` to reflect this. Verified empirically: real bonus ex-dates inside the
dataset window (BHEL 2017-09-28, BAJAJFINSV 2022-09-14, BPCL Jul-2017/May-2024, ASHOKLEY
2025-07-16) show ZERO price gap in the ingested data.

Checking this module's own output confirmed the consequence: all 17 candidates it scored
HIGH_CONFIDENCE on the live NIFTY100 dataset were false positives (see PROJECT_STATUS.md
section 3.2.1 for the full per-symbol check). The "traded value continuity" heuristic below
does NOT reliably distinguish a bonus from a market-wide panic day, because panic days
(COVID crash week, March 2020; election-result crash, 2024-06-04) elevate volume for
essentially every stock simultaneously — which can satisfy the continuity test even though
nothing corporate happened. Do not treat a HIGH_CONFIDENCE hit as evidence; it is a lead for
a human/external check, and on this evidence its hit rate on real data is currently 0%.

Genuine remaining use: catching demerger/spin-off discontinuities that Kite's adjustment
does NOT retroactively splice (there's no single ratio for a spin-off) — e.g. CGPOWER's
2015-10-01 demerger of Crompton Greaves Consumer Electricals, the dataset's single largest
move (+190.67%) and a real event, not a defect. For that narrower purpose this module is
still useful as a discontinuity scanner; for inferring bonuses/splits to backward-adjust, it
is currently unreliable and its output must not be applied via `corporate_actions/adjuster.py`
without independent confirmation.

ORIGINAL DESIGN RATIONALE (superseded above, kept for context)
================================================================
WHY THIS EXISTS
===============
The original premise was that `backfill.py` stores every bar with `is_adjusted=False` and
the Kite provider performs no corporate action adjustment — this is now known to be false,
see the correction above. The ingested NIFTY 100 data shows a largest daily move of +190.67%
and pooled excess kurtosis of 156, both far outside normal equity behaviour; this is now
understood to be the CGPOWER demerger and genuine crash-day volatility, not unadjusted
corporate actions.

An unadjusted 1:1 bonus, if it existed in this data, would appear as a -50% overnight gap
that never happened, stopping out every long position in that name on a date with no
relationship to the strategy. Research Cycle 1's symptom was "almost every trade hits its
stop" — this remains worth guarding against in principle, even though the specific mechanism
assumed here (Kite feed unadjusted) turned out not to apply.

WHY DETECTION RATHER THAN JUST FETCHING
=======================================
The authoritative source is the exchange. `NSECorporateActionsProvider` returns `[]` — the
fetch was never implemented — and this module does NOT invent an endpoint to replace it.

Detection is complementary and, for this purpose, better first:

  - it works offline, against data already in the database
  - it finds actions the vendor feed omits, which is the failure mode that silently corrupts
    a backtest
  - it produces a specific, checkable claim ("RELIANCE 2017-09-XX, implied ratio 0.500,
    matches 1:1 BONUS") that a human can verify against one NSE circular in seconds

Detected actions are written with `verified=False` and `source='PRICE_INFERRED'`. They must
be confirmed against the exchange record before any result depending on them is reported.
Inference locates candidates; it does not establish fact.

THE STRONGEST SIGNAL: TRADED VALUE CONTINUITY
=============================================
A price crash and a stock split look identical in a close-to-close return series. They do
not look identical in traded value.

On a split or bonus ex-date the share count changes, so quantity traded scales up by
roughly the same factor the price scales down — traded value (price x volume) stays broadly
continuous. In a genuine crash, price falls AND traded value usually spikes on panic volume.

So: price discontinuous + traded value continuous => corporate action.

See docs/research/REPO_AUDIT_2026-08-06.md and docs/PROJECT_STATUS.md section 3.2.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("tradecraft.ca_detector")

DETECTOR_VERSION = "1.0.0"

# A move beyond this is not explainable by ordinary trading and warrants classification.
GAP_THRESHOLD = 0.20

# How close an implied multiplier must be to a standard ratio to be called a match.
RATIO_TOLERANCE = 0.02

# Sessions either side of the gap used for the median traded-value comparison.
VALUE_WINDOW = 10

# How much closer (in log distance) traded value must sit to one hypothesis than the other
# before the discriminant is treated as decisive rather than inconclusive.
VALUE_DISCRIMINANT_MARGIN = 0.20

# Standard Indian corporate action multipliers.
#
#   bonus a:b (a new shares for every b held)  -> price multiplier = b / (a + b)
#   face value split F1 -> F2                  -> price multiplier = F2 / F1
#   consolidation (reverse split) b:a          -> price multiplier > 1
#
# Ratios are stored as (numerator, denominator) describing the PRICE multiplier, so
# reconstruction is exact rather than floating point.
STANDARD_ACTIONS: list[tuple[str, str, Fraction]] = [
    # --- bonuses / splits: price falls -------------------------------------------------
    ("BONUS", "1:1", Fraction(1, 2)),
    ("BONUS", "2:1", Fraction(1, 3)),
    ("BONUS", "3:1", Fraction(1, 4)),
    ("BONUS", "4:1", Fraction(1, 5)),
    ("BONUS", "1:2", Fraction(2, 3)),
    ("BONUS", "2:3", Fraction(3, 5)),
    ("BONUS", "3:2", Fraction(2, 5)),
    ("BONUS", "1:3", Fraction(3, 4)),
    ("BONUS", "1:4", Fraction(4, 5)),
    ("BONUS", "1:5", Fraction(5, 6)),
    ("BONUS", "1:10", Fraction(10, 11)),
    ("SPLIT", "10->1", Fraction(1, 10)),
    ("SPLIT", "10->2", Fraction(1, 5)),
    ("SPLIT", "10->5", Fraction(1, 2)),
    ("SPLIT", "5->1", Fraction(1, 5)),
    ("SPLIT", "5->2", Fraction(2, 5)),
    ("SPLIT", "2->1", Fraction(1, 2)),
    ("SPLIT", "1->0.5", Fraction(1, 2)),
    ("SPLIT", "100->10", Fraction(1, 10)),
    ("SPLIT", "100->5", Fraction(1, 20)),
    ("SPLIT", "100->2", Fraction(1, 50)),
    ("SPLIT", "100->1", Fraction(1, 100)),
    # --- consolidations: price rises ---------------------------------------------------
    ("CONSOLIDATION", "1:2", Fraction(2, 1)),
    ("CONSOLIDATION", "1:3", Fraction(3, 1)),
    ("CONSOLIDATION", "1:5", Fraction(5, 1)),
    ("CONSOLIDATION", "1:10", Fraction(10, 1)),
]


@dataclass
class DetectedAction:
    """A candidate corporate action inferred from a price discontinuity."""

    symbol: str
    instrument_id: Any
    ex_date: date
    prev_close: float
    close: float
    implied_multiplier: float
    action_type: str | None
    ratio_label: str | None
    ratio_fraction: Fraction | None
    ratio_error: float | None
    traded_value_ratio: float | None
    volume_ratio: float | None
    confidence: str
    alternatives: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def pct_change(self) -> float:
        return self.implied_multiplier - 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ex_date": self.ex_date.isoformat(),
            "prev_close": self.prev_close,
            "close": self.close,
            "pct_change": self.pct_change,
            "implied_multiplier": self.implied_multiplier,
            "action_type": self.action_type,
            "ratio": self.ratio_label,
            "ratio_error": self.ratio_error,
            "traded_value_ratio": self.traded_value_ratio,
            "volume_ratio": self.volume_ratio,
            "confidence": self.confidence,
            "ambiguous_alternatives": self.alternatives,
            "reasons": self.reasons,
        }


@dataclass
class DetectionReport:
    detector_version: str = DETECTOR_VERSION
    actions: list[DetectedAction] = field(default_factory=list)
    instruments_scanned: int = 0
    bars_scanned: int = 0

    @property
    def high(self) -> list[DetectedAction]:
        return [a for a in self.actions if a.confidence == "HIGH"]

    @property
    def medium(self) -> list[DetectedAction]:
        return [a for a in self.actions if a.confidence == "MEDIUM"]

    @property
    def unexplained(self) -> list[DetectedAction]:
        return [a for a in self.actions if a.confidence == "UNEXPLAINED"]

    def render(self) -> str:
        out: list[str] = []
        out.append("=" * 82)
        out.append(f"  CORPORATE ACTION DETECTION  (detector v{self.detector_version})")
        out.append("=" * 82)
        out.append(
            f"  scanned {self.instruments_scanned} instruments / {self.bars_scanned} bars  "
            f"| gaps >= {GAP_THRESHOLD:.0%}: {len(self.actions)}"
        )
        out.append("-" * 82)

        for label, group in (
            ("HIGH CONFIDENCE — ratio matched AND traded value continuous", self.high),
            ("MEDIUM CONFIDENCE — one corroborating signal only", self.medium),
            ("UNEXPLAINED — no standard ratio matched", self.unexplained),
        ):
            out.append(f"\n  {label}: {len(group)}")
            for a in sorted(group, key=lambda x: (x.symbol, x.ex_date)):
                ratio = f"{a.action_type} {a.ratio_label}" if a.action_type else "—"
                out.append(
                    f"    {a.symbol:<14} {a.ex_date}  {a.prev_close:>10.2f} -> {a.close:>10.2f}"
                    f"  {a.pct_change:>+8.1%}  x{a.implied_multiplier:.4f}  {ratio}"
                )
                for r in a.reasons:
                    out.append(f"        - {r}")

        out.append("\n" + "-" * 82)
        if self.high or self.medium:
            out.append("  These are INFERRED, not verified. Confirm each against the NSE")
            out.append("  circular for that ex-date before relying on adjusted prices:")
            out.append("      python -m tradecraft data corporate-actions import <file.csv>")
        if self.unexplained:
            out.append("  UNEXPLAINED gaps are either genuine market events or data errors.")
            out.append("  Inspect before treating the affected series as clean.")
        out.append("=" * 82)
        return "\n".join(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector_version": self.detector_version,
            "instruments_scanned": self.instruments_scanned,
            "bars_scanned": self.bars_scanned,
            "counts": {
                "high": len(self.high),
                "medium": len(self.medium),
                "unexplained": len(self.unexplained),
            },
            "actions": [a.to_dict() for a in self.actions],
        }


class CorporateActionDetector:
    """Infers candidate corporate actions from unexplained price discontinuities."""

    def __init__(
        self,
        gap_threshold: float = GAP_THRESHOLD,
        ratio_tolerance: float = RATIO_TOLERANCE,
    ) -> None:
        self.gap_threshold = gap_threshold
        self.ratio_tolerance = ratio_tolerance

    # ------------------------------------------------------------------ ratio matching

    def match_ratio(
        self, multiplier: float
    ) -> tuple[str | None, str | None, Fraction | None, float | None]:
        """Match an implied price multiplier against standard corporate action ratios.

        Returns the best (action_type, ratio_label, fraction, relative_error), or all None.
        Error is relative rather than absolute so a 1:100 split is judged as tightly as a
        1:1 bonus.

        Use `match_ratio_candidates` when the ambiguity matters — several distinct corporate
        actions share a price multiplier and cannot be told apart from price alone.
        """
        cands = self.match_ratio_candidates(multiplier)
        if not cands:
            return None, None, None, None
        t, label, frac, err = cands[0]
        return t, label, frac, err

    def match_ratio_candidates(
        self, multiplier: float
    ) -> list[tuple[str, str, Fraction, float]]:
        """All standard ratios consistent with this multiplier, best first.

        AMBIGUITY IS REAL AND MUST NOT BE HIDDEN
        =======================================
        Different corporate actions produce identical price behaviour. A 4:1 bonus, a 5->1
        face value split and a 10->2 split all multiply the price by exactly 0.2. Nothing in
        the price series distinguishes them.

        Returning a single "best" match here would be arbitrary — decided by list ordering
        rather than by evidence — and would then be written into the database as though it
        were a finding. Every alternative is returned so the human verifying against the NSE
        circular knows what they are choosing between.
        """
        out: list[tuple[str, str, Fraction, float]] = []
        for action_type, label, frac in STANDARD_ACTIONS:
            expected = float(frac)
            if expected <= 0:
                continue
            err = abs(multiplier - expected) / expected
            if err <= self.ratio_tolerance:
                out.append((action_type, label, frac, err))
        return sorted(out, key=lambda c: c[3])

    # ------------------------------------------------------------------ value continuity

    @staticmethod
    def _median_traded_value(
        bars: list[dict[str, Any]], start: int, end: int
    ) -> float | None:
        """Median traded value over a window, used instead of a single adjacent bar.

        Daily volume is extremely noisy — comparing one bar to the next produces ratios that
        swing 2x on ordinary trading, which is enough to misclassify a real corporate action
        as a market event. A short median either side of the gap is far more stable.
        """
        vals = [
            b["close"] * b["volume"]
            for b in bars[max(0, start) : end]
            if b["volume"] > 0 and b["close"] > 0
        ]
        return statistics.median(vals) if vals else None

    @staticmethod
    def _value_verdict(
        value_ratio: float | None, multiplier: float
    ) -> tuple[bool, str | None]:
        """Decide whether traded value behaved like a share-count change or a repricing.

        A fixed "continuity band" around 1.0 does not work, because the correct answer
        depends on the size of the price move. A 37% crash with unchanged share volume
        produces a traded-value ratio of 0.63 — comfortably inside any loose band, yet it is
        emphatically NOT a corporate action.

        The two hypotheses make different, testable predictions:

            corporate action  -> share count absorbs the price change, value_ratio ~ 1.0
            genuine repricing -> share count unchanged,               value_ratio ~ multiplier

        So compare which prediction the observation sits closer to, in log space (scale-free,
        so a 1:100 split is judged as fairly as a 1:1 bonus). When the two are nearly
        equidistant the evidence is genuinely weak and neither is claimed.
        """
        if value_ratio is None or value_ratio <= 0 or multiplier <= 0:
            return False, None

        dist_action = abs(math.log(value_ratio))
        dist_repricing = abs(math.log(value_ratio / multiplier))

        if dist_action + VALUE_DISCRIMINANT_MARGIN < dist_repricing:
            return True, (
                f"traded value held steady across the gap (ratio {value_ratio:.2f} vs "
                f"{multiplier:.2f} expected if volume were unchanged) — price moved but "
                "rupees traded did not, the signature of a share-count change"
            )
        if dist_repricing + VALUE_DISCRIMINANT_MARGIN < dist_action:
            return False, (
                f"traded value fell with price (ratio {value_ratio:.2f}, tracking the "
                f"{multiplier:.2f} price multiplier) — share count unchanged, consistent "
                "with a genuine market event"
            )
        return False, (
            f"traded value ratio {value_ratio:.2f} is inconclusive — roughly equidistant "
            "from both a share-count change and a repricing"
        )

    # ------------------------------------------------------------------ data loading

    def _load(self, session: Session) -> dict[str, list[dict[str, Any]]]:
        rows = session.execute(
            text(
                """
                SELECT i.symbol AS symbol, i.id AS iid, m.trading_date AS d,
                       m.close AS c, m.volume AS v
                FROM market_bars m
                JOIN instruments i ON i.id = m.instrument_id
                WHERE m.is_adjusted = true
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
                {
                    "iid": r["iid"],
                    "date": d,
                    "close": float(r["c"]),
                    "volume": int(r["v"] or 0),
                }
            )
        return dict(series)

    # ------------------------------------------------------------------ detection

    def run(self, session: Session) -> DetectionReport:
        return self.detect(self._load(session))

    def detect(self, series: dict[str, list[dict[str, Any]]]) -> DetectionReport:
        report = DetectionReport()
        report.instruments_scanned = len(series)
        report.bars_scanned = sum(len(b) for b in series.values())

        for symbol, bars in series.items():
            for i in range(1, len(bars)):
                prev, cur = bars[i - 1], bars[i]
                if prev["close"] <= 0:
                    continue

                mult = cur["close"] / prev["close"]
                if abs(mult - 1.0) < self.gap_threshold:
                    continue

                candidates = self.match_ratio_candidates(mult)
                action_type, label, frac, err = (
                    candidates[0] if candidates else (None, None, None, None)
                )

                # Windowed medians, not adjacent bars — daily volume noise alone can swing
                # a single-bar ratio by 2x and misclassify a genuine corporate action.
                before = self._median_traded_value(bars, i - VALUE_WINDOW, i)
                after = self._median_traded_value(bars, i, i + VALUE_WINDOW)
                value_ratio = (after / before) if (before and after and before > 0) else None
                vol_ratio = (
                    cur["volume"] / prev["volume"] if prev["volume"] > 0 else None
                )

                reasons: list[str] = []
                if action_type:
                    reasons.append(
                        f"implied multiplier {mult:.4f} matches {action_type} {label} "
                        f"({float(frac):.4f}), relative error {err:.2%}"
                    )
                    if len(candidates) > 1:
                        alts = ", ".join(f"{t} {lb}" for t, lb, _f, _e in candidates[1:])
                        reasons.append(
                            f"AMBIGUOUS — indistinguishable from price alone: {alts}. "
                            "The NSE circular decides which it was."
                        )
                else:
                    reasons.append(
                        f"implied multiplier {mult:.4f} matches no standard ratio "
                        f"within {self.ratio_tolerance:.0%}"
                    )

                value_continuous, verdict_note = self._value_verdict(value_ratio, mult)
                if verdict_note:
                    reasons.append(verdict_note)

                # Share count moves opposite to price on a split/bonus.
                if vol_ratio is not None and frac is not None and float(frac) > 0:
                    expected_vol = 1.0 / float(frac)
                    if expected_vol > 0 and 0.4 <= (vol_ratio / expected_vol) <= 2.5:
                        reasons.append(
                            f"volume scaled by {vol_ratio:.2f}x, near the {expected_vol:.2f}x "
                            "implied by the share-count change"
                        )

                if action_type and value_continuous:
                    confidence = "HIGH"
                elif action_type or value_continuous:
                    confidence = "MEDIUM"
                else:
                    confidence = "UNEXPLAINED"

                report.actions.append(
                    DetectedAction(
                        symbol=symbol,
                        instrument_id=cur["iid"],
                        ex_date=cur["date"],
                        prev_close=prev["close"],
                        close=cur["close"],
                        implied_multiplier=mult,
                        action_type=action_type,
                        ratio_label=label,
                        ratio_fraction=frac,
                        ratio_error=err,
                        traded_value_ratio=value_ratio,
                        volume_ratio=vol_ratio,
                        confidence=confidence,
                        alternatives=[f"{t} {lb}" for t, lb, _f, _e in candidates[1:]],
                        reasons=reasons,
                    )
                )

        report.actions.sort(key=lambda a: (a.symbol, a.ex_date))
        return report
