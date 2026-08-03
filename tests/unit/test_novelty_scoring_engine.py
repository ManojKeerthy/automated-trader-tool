"""Unit tests for NoveltyScoringEngine."""

import pytest
from tradecraft.research.novelty_scoring_engine import NoveltyScoringEngine
from tradecraft.research.hypothesis_registry import HypothesisRecord


def test_novelty_scoring_engine():
    engine = NoveltyScoringEngine()

    novel_hypo = HypothesisRecord(
        hypothesis_uuid="hypo-nov-1",
        hypothesis_name="Earnings Quality Premium",
        parent_hypothesis_uuid=None,
        economic_rationale="Gross profitability premium in liquid Indian equities.",
        behavioural_rationale="Under-estimation of sustainable return on equity.",
        expected_market_behaviour="Outperformance during volatile regimes.",
        falsification_criteria="PF < 1.25",
        supporting_literature=["Novy-Marx"],
    )
    report = engine.evaluate_novelty(novel_hypo)
    assert report.is_sufficiently_novel is True
    assert report.novelty_score >= 0.65

    recycled_hypo = HypothesisRecord(
        hypothesis_uuid="hypo-rec-1",
        hypothesis_name="Donchian Breakout Confirmation ATR",
        parent_hypothesis_uuid=None,
        economic_rationale="Donchian breakout consolidation confirmation resistance high ATR.",
        behavioural_rationale="Donchian breakout consolidation confirmation resistance high ATR.",
        expected_market_behaviour="Breakout continuation.",
        falsification_criteria="PF < 1.25",
        supporting_literature=["Paper"],
    )
    rep_rec = engine.evaluate_novelty(recycled_hypo)
    assert rep_rec.is_sufficiently_novel is False
    assert rep_rec.novelty_score < 0.65
