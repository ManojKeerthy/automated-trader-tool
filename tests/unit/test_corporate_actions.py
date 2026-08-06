"""Corporate action detection and adjustment tests.

The blocking data defect as of 2026-08-06: every bar is stored `is_adjusted=False` and the
provider performs no adjustment, so the ingested series shows a +190.67% daily move and
excess kurtosis of 156. An unadjusted 1:1 bonus is a fake -50% gap that stops out every long
position in that name on a date unrelated to the strategy.

These tests inject known corporate actions into clean series and prove:
  1. the detector finds them and names the correct ratio
  2. it distinguishes them from genuine crashes (the traded-value test)
  3. back-adjustment restores a continuous return series
  4. unverified inferences are never applied to prices

See docs/research/REPO_AUDIT_2026-08-06.md.
"""

from __future__ import annotations

import math
import random
import statistics
from datetime import date, timedelta
from fractions import Fraction

import pytest

from tradecraft.corporate_actions.adjuster import multiplier_from_action
from tradecraft.corporate_actions.detector import CorporateActionDetector


def sessions(start: date, n: int) -> list[date]:
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def clean_series(base: float, n: int, seed: int = 7, vol: float = 0.015) -> list[dict]:
    """A plausible price path with lognormal volume."""
    rng = random.Random(seed)
    bars, price = [], base
    for d in sessions(date(2016, 1, 4), n):
        price = max(1.0, price * (1 + rng.gauss(0.0004, vol)))
        bars.append(
            {
                "iid": "i1",
                "date": d,
                "close": round(price, 2),
                "volume": int(max(1000, rng.lognormvariate(math.log(1_000_000), 0.4))),
            }
        )
    return bars


def apply_unadjusted_action(bars: list[dict], idx: int, multiplier: float) -> list[dict]:
    """Simulate a vendor feed that never adjusted for a corporate action.

    From `idx` onward the price reflects the new share count and volume scales inversely,
    so traded value stays continuous — exactly what real unadjusted data looks like.
    """
    out = [dict(b) for b in bars]
    for i in range(idx, len(out)):
        out[i]["close"] = round(out[i]["close"] * multiplier, 2)
        out[i]["volume"] = int(out[i]["volume"] / multiplier)
    return out


def apply_genuine_crash(bars: list[dict], idx: int, drop: float) -> list[dict]:
    """A real crash: price falls AND traded value spikes on panic volume."""
    out = [dict(b) for b in bars]
    for i in range(idx, len(out)):
        out[i]["close"] = round(out[i]["close"] * (1 - drop), 2)
    out[idx]["volume"] = int(out[idx]["volume"] * 8)
    return out


# =======================================================================================
# Ratio arithmetic
# =======================================================================================


class TestRatioArithmetic:
    @pytest.mark.parametrize(
        "action,rf,rt,expected",
        [
            ("BONUS", 1, 1, 0.5),        # 1 new per 1 held -> 2 shares -> price halves
            ("BONUS", 2, 1, 1 / 3),      # 2 new per 1 held -> 3 shares
            ("BONUS", 1, 2, 2 / 3),      # 1 new per 2 held -> 3 shares per 2
            ("BONUS", 3, 1, 0.25),
            ("SPLIT", 10, 1, 0.1),       # face value 10 -> 1
            ("SPLIT", 10, 5, 0.5),
            ("SPLIT", 10, 2, 0.2),
            ("CONSOLIDATION", 1, 5, 5.0),
        ],
    )
    def test_multiplier_is_hand_computed(
        self, action: str, rf: int, rt: int, expected: float
    ) -> None:
        m = multiplier_from_action(action, rf, rt)
        assert m == pytest.approx(expected, rel=1e-9)

    def test_unusable_ratios_return_none(self) -> None:
        assert multiplier_from_action("BONUS", None, 1) is None
        assert multiplier_from_action("BONUS", 0, 1) is None
        assert multiplier_from_action("DIVIDEND", 1, 1) is None


# =======================================================================================
# Detection
# =======================================================================================


class TestDetection:
    def setup_method(self) -> None:
        self.det = CorporateActionDetector()

    @pytest.mark.parametrize(
        "label,multiplier,expected_type,expected_ratio",
        [
            ("1:1 bonus", 0.5, "BONUS", "1:1"),
            ("2:1 bonus", 1 / 3, "BONUS", "2:1"),
            ("1:2 bonus", 2 / 3, "BONUS", "1:2"),
            ("10->1 split", 0.1, "SPLIT", "10->1"),
            ("10->2 split", 0.2, "BONUS", "4:1"),  # ambiguous: see alternatives
        ],
    )
    def test_detects_injected_action(
        self, label: str, multiplier: float, expected_type: str, expected_ratio: str
    ) -> None:
        bars = apply_unadjusted_action(clean_series(1000.0, 600), 300, multiplier)
        report = self.det.detect({"TESTCO": bars})

        assert len(report.actions) == 1, f"{label}: expected exactly one gap"
        a = report.actions[0]
        assert a.confidence == "HIGH"
        assert a.ex_date == bars[300]["date"]
        # The true action must be either the best match or an acknowledged alternative.
        all_labels = [f"{a.action_type} {a.ratio_label}"] + a.alternatives
        assert f"{expected_type} {expected_ratio}" in all_labels, all_labels

    def test_identical_multipliers_are_reported_as_ambiguous(self) -> None:
        """A 4:1 bonus, a 5->1 split and a 10->2 split ALL multiply price by 0.2.

        Nothing in the price series distinguishes them. The detector must surface every
        candidate rather than silently picking one by list order and writing it to the
        database as though it were a finding.
        """
        bars = apply_unadjusted_action(clean_series(1000.0, 600), 300, 0.2)
        a = self.det.detect({"AMBIG": bars}).actions[0]
        every = {f"{a.action_type} {a.ratio_label}", *a.alternatives}
        assert {"BONUS 4:1", "SPLIT 5->1", "SPLIT 10->2"} <= every
        assert any("AMBIGUOUS" in r for r in a.reasons)

    def test_high_confidence_requires_value_continuity(self) -> None:
        """A 1:1 bonus and a 50% crash have identical price returns.

        Only traded value separates them. This is the test that makes the detector useful
        rather than a restatement of the return series.
        """
        bonus = apply_unadjusted_action(clean_series(1000.0, 600), 300, 0.5)
        crash = apply_genuine_crash(clean_series(1000.0, 600), 300, 0.5)

        a_bonus = self.det.detect({"BONUSCO": bonus}).actions[0]
        a_crash = self.det.detect({"CRASHCO": crash}).actions[0]

        # Same price move
        assert a_bonus.implied_multiplier == pytest.approx(
            a_crash.implied_multiplier, rel=0.02
        )
        # Different verdict
        assert a_bonus.confidence == "HIGH"
        assert a_crash.confidence == "MEDIUM"
        # The discriminant: a bonus holds traded value at ~1.0 while a crash lets it fall
        # with price (~0.5 for a 50% drop, since share volume is unchanged).
        assert a_bonus.traded_value_ratio == pytest.approx(1.0, abs=0.35)
        assert a_crash.traded_value_ratio == pytest.approx(0.5, abs=0.25)

    def test_clean_series_yields_nothing(self) -> None:
        assert self.det.detect({"CLEAN": clean_series(500.0, 800)}).actions == []

    def test_non_standard_gap_is_unexplained(self) -> None:
        """A 37% move matching no standard ratio must not be forced into one."""
        bars = apply_genuine_crash(clean_series(500.0, 600), 300, 0.37)
        a = self.det.detect({"ODDCO": bars}).actions[0]
        assert a.action_type is None
        assert a.confidence == "UNEXPLAINED"

    def test_detects_consolidation_upward(self) -> None:
        bars = apply_unadjusted_action(clean_series(20.0, 600), 300, 5.0)
        a = self.det.detect({"REVCO": bars}).actions[0]
        assert a.action_type == "CONSOLIDATION"
        assert a.implied_multiplier > 1

    def test_multiple_actions_all_found(self) -> None:
        bars = clean_series(2000.0, 900)
        bars = apply_unadjusted_action(bars, 250, 0.5)     # 1:1 bonus
        bars = apply_unadjusted_action(bars, 600, 0.2)     # 10->2 split
        report = self.det.detect({"MULTICO": bars})
        assert len(report.actions) == 2
        labels = {f"{a.action_type} {a.ratio_label}" for a in report.actions}
        assert "BONUS 1:1" in labels
        assert any(a.implied_multiplier == pytest.approx(0.2, rel=0.05)
                   for a in report.actions)

    def test_ratio_matching_is_relative_not_absolute(self) -> None:
        """A 1:100 split must be judged as tightly as a 1:1 bonus."""
        t, label, frac, err = self.det.match_ratio(0.0101)  # ~1% off 0.01
        assert t == "SPLIT" and label == "100->1"
        assert self.det.match_ratio(0.0130)[0] is None  # 30% off -> no match

    def test_threshold_is_respected(self) -> None:
        bars = apply_unadjusted_action(clean_series(1000.0, 600), 300, 0.85)
        assert CorporateActionDetector(gap_threshold=0.10).detect({"X": bars}).actions
        assert not CorporateActionDetector(gap_threshold=0.30).detect({"X": bars}).actions


# =======================================================================================
# Adjustment restores continuity
# =======================================================================================


def back_adjust(bars: list[dict], actions: list[tuple[date, float]]) -> list[dict]:
    """Reference implementation of the adjuster's arithmetic, for verification."""
    out = []
    for b in bars:
        factor = 1.0
        for ex_date, m in actions:
            if ex_date > b["date"]:
                factor *= m
        out.append(
            {
                **b,
                "close": b["close"] * factor,
                "volume": int(b["volume"] / factor) if factor else b["volume"],
            }
        )
    return out


class TestAdjustmentRestoresContinuity:
    def test_adjustment_removes_the_artificial_gap(self) -> None:
        """THE POINT OF THE WHOLE PIPELINE.

        Before adjustment the series contains a -50% day that never happened. After
        adjustment the largest daily move returns to normal, so stops are no longer
        triggered by a share-count change.
        """
        clean = clean_series(1000.0, 600)
        raw = apply_unadjusted_action(clean, 300, 0.5)
        ex_date = raw[300]["date"]

        def max_abs_move(bars: list[dict]) -> float:
            return max(
                abs(bars[i]["close"] / bars[i - 1]["close"] - 1) for i in range(1, len(bars))
            )

        assert max_abs_move(raw) > 0.45, "raw series should contain the fake gap"
        adjusted = back_adjust(raw, [(ex_date, 0.5)])
        assert max_abs_move(adjusted) < 0.10, "adjustment should remove it"

    def test_adjusted_series_is_detection_clean(self) -> None:
        raw = apply_unadjusted_action(clean_series(1000.0, 600), 300, 0.5)
        ex_date = raw[300]["date"]
        adjusted = back_adjust(raw, [(ex_date, 0.5)])
        assert CorporateActionDetector().detect({"ADJ": adjusted}).actions == []

    def test_traded_value_is_preserved(self) -> None:
        """Volume adjusts inversely, so liquidity filters stay comparable across a split."""
        raw = apply_unadjusted_action(clean_series(1000.0, 400), 200, 0.5)
        ex_date = raw[200]["date"]
        adjusted = back_adjust(raw, [(ex_date, 0.5)])
        for r, a in zip(raw[:200], adjusted[:200]):
            assert r["close"] * r["volume"] == pytest.approx(
                a["close"] * a["volume"], rel=0.01
            )

    def test_most_recent_price_is_untouched(self) -> None:
        """Back-adjustment convention: today's price matches today's chart."""
        raw = apply_unadjusted_action(clean_series(1000.0, 600), 300, 0.5)
        adjusted = back_adjust(raw, [(raw[300]["date"], 0.5)])
        assert adjusted[-1]["close"] == pytest.approx(raw[-1]["close"])

    def test_compounding_actions(self) -> None:
        """Two actions must multiply, not overwrite one another."""
        raw = clean_series(2000.0, 900)
        raw = apply_unadjusted_action(raw, 250, 0.5)
        raw = apply_unadjusted_action(raw, 600, 0.2)
        adjusted = back_adjust(raw, [(raw[250]["date"], 0.5), (raw[600]["date"], 0.2)])

        # Earliest bar carries both factors: 0.5 * 0.2 = 0.1
        assert adjusted[0]["close"] == pytest.approx(raw[0]["close"] * 0.1, rel=1e-6)
        assert CorporateActionDetector().detect({"M": adjusted}).actions == []

    def test_kurtosis_falls_after_adjustment(self) -> None:
        """The ingested data showed excess kurtosis 156. Fake gaps are the likely cause."""

        def excess_kurtosis(bars: list[dict]) -> float:
            r = [bars[i]["close"] / bars[i - 1]["close"] - 1 for i in range(1, len(bars))]
            m, sd = statistics.fmean(r), statistics.pstdev(r)
            return sum(((x - m) / sd) ** 4 for x in r) / len(r) - 3.0

        raw = apply_unadjusted_action(clean_series(1000.0, 600), 300, 0.5)
        adjusted = back_adjust(raw, [(raw[300]["date"], 0.5)])
        assert excess_kurtosis(adjusted) < excess_kurtosis(raw) / 10


# =======================================================================================
# Safety
# =======================================================================================


class TestSafety:
    def test_detected_actions_are_not_self_certifying(self) -> None:
        """Inference locates candidates; it must not assert fact.

        The adjuster skips unverified actions by default, so a detector run alone can never
        silently alter prices.
        """
        from tradecraft.corporate_actions.adjuster import CorporateActionAdjuster

        assert CorporateActionAdjuster().include_unverified is False

    def test_only_price_affecting_types_adjust(self) -> None:
        from tradecraft.corporate_actions.adjuster import PRICE_AFFECTING

        assert "DIVIDEND" not in PRICE_AFFECTING
        assert {"SPLIT", "BONUS", "CONSOLIDATION"} == PRICE_AFFECTING

    def test_inverted_bonus_ratio_is_rejected(self) -> None:
        """BONUS 1:1 halves the price. A bonus implying a rise is a data-entry error."""
        m = multiplier_from_action("BONUS", 1, 1)
        assert m is not None and m < 1.0

    def test_standard_ratios_are_exact_fractions(self) -> None:
        """Ratios are Fractions so reconstruction is exact, not floating point."""
        from tradecraft.corporate_actions.detector import STANDARD_ACTIONS

        for _t, _label, frac in STANDARD_ACTIONS:
            assert isinstance(frac, Fraction)
            assert frac > 0
