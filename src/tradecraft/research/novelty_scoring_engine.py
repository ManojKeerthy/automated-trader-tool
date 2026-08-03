"""Novelty Scoring Engine for Graveyard lineage collision detection."""

from dataclasses import dataclass
from typing import Any

from tradecraft.research.hypothesis_registry import HypothesisRecord


@dataclass
class NoveltyReport:
    hypothesis_uuid: str
    novelty_score: float  # 0.0 (identical to graveyard) to 1.0 (100% novel)
    highest_similarity_lineage: str
    is_sufficiently_novel: bool  # True if novelty_score >= 0.65 (similarity <= 0.35)
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_uuid": self.hypothesis_uuid,
            "novelty_score": self.novelty_score,
            "highest_similarity_lineage": self.highest_similarity_lineage,
            "is_sufficiently_novel": self.is_sufficiently_novel,
            "explanation": self.explanation,
        }


class NoveltyScoringEngine:
    """Quantitative similarity engine protecting against recycled Graveyard strategies."""

    GRAVEYARD_LINEAGES = {
        "strat_trend_pullback": {
            "trend",
            "pullback",
            "ema",
            "rsi",
            "continuation",
            "bounce",
            "dip",
        },
        "strat_momentum_rs": {
            "momentum",
            "relative",
            "strength",
            "nifty",
            "rank",
            "outperformance",
            "rs",
        },
        "strat_breakout_confirm": {
            "breakout",
            "donchian",
            "consolidation",
            "atr",
            "resistance",
            "high",
            "confirmation",
        },
        "strat_mean_reversion": {
            "mean",
            "reversion",
            "oversold",
            "rsi",
            "stretch",
            "reversal",
            "oscillator",
        },
    }

    def evaluate_novelty(self, hypothesis: HypothesisRecord) -> NoveltyReport:
        """Evaluate text token similarity against abandoned graveyard strategy keywords."""
        text = f"{hypothesis.hypothesis_name} {hypothesis.economic_rationale} {hypothesis.behavioural_rationale} {hypothesis.expected_market_behaviour}".lower()
        tokens: set[str] = set(text.replace("-", " ").replace("_", " ").split())

        max_similarity = 0.0
        most_similar_lineage = "NONE"

        for lineage_id, kw_set in self.GRAVEYARD_LINEAGES.items():
            intersection = tokens.intersection(kw_set)
            union = tokens.union(kw_set)
            similarity = len(intersection) / len(union) if union else 0.0

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_lineage = lineage_id

        novelty_score = round(1.0 - max_similarity, 4)
        is_novel = novelty_score >= 0.65  # Equivalent to similarity <= 0.35

        explanation = (
            f"Novelty score {novelty_score} vs Graveyard lineage '{most_similar_lineage}' "
            f"(Similarity: {round(max_similarity, 4)}). "
            f"{'PASS: Sufficient novelty.' if is_novel else 'FAIL: High similarity to abandoned strategy lineage.'}"
        )

        return NoveltyReport(
            hypothesis_uuid=hypothesis.hypothesis_uuid,
            novelty_score=novelty_score,
            highest_similarity_lineage=most_similar_lineage,
            is_sufficiently_novel=is_novel,
            explanation=explanation,
        )
