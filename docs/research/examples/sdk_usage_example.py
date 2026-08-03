"""Example: Using the Public Research SDK to query registered features and hypotheses."""

from datetime import date
from tradecraft.sdk import ResearchClient
from tradecraft.research.hypothesis_registry import HypothesisRecord

def main():
    client = ResearchClient()

    # 1. List registered features
    features = client.list_registered_features()
    print(f"Registered features count: {len(features)}")
    for f in features:
        print(f" - {f.feature_name} (UUID: {f.feature_uuid})")

    # 2. Register a new hypothesis
    hypo = HypothesisRecord(
        hypothesis_uuid="hypo-cross-sec-mom-v1",
        hypothesis_name="Cross-Sectional Momentum in NIFTY 250",
        parent_hypothesis_uuid=None,
        economic_rationale="Persistence of institutional buying in top 25th percentile relative strength stocks.",
        behavioural_rationale="Under-reaction to fundamental earnings momentum.",
        expected_market_behaviour="Outperformance during trending market regimes.",
        falsification_criteria="Net expectancy R < 0.25R or Profit Factor < 1.30.",
        supporting_literature=["Jegadeesh and Titman (1993)"],
    )
    client.register_hypothesis(hypo)
    print(f"Registered hypothesis: {hypo.hypothesis_name}")

if __name__ == "__main__":
    main()
