"""Unit tests for FeatureRegistry and FeatureDefinition."""

import pytest
from tradecraft.research.feature_registry import FeatureDefinition, FeatureRegistry, FeatureLineage


def test_feature_registry_initialization():
    reg = FeatureRegistry()
    feats = reg.list_features()
    assert len(feats) == 12
    rsi_feat = reg.get_feature("RSI")
    assert rsi_feat is not None
    assert rsi_feat.feature_name == "RSI"
    assert len(rsi_feat.checksum) == 64


def test_custom_feature_registration():
    reg = FeatureRegistry()
    lineage = FeatureLineage(depends_on=["Close"], raw_features=["Close"])
    defn = FeatureDefinition(
        feature_uuid="feat-custom-1",
        feature_name="CUSTOM_MOMENTUM",
        description="Custom momentum indicator",
        mathematical_definition="Close - Close[20]",
        required_inputs=["Close"],
        lookback_period=20,
        warmup_period=20,
        lineage=lineage,
    )
    uuid_res = reg.register_feature(defn)
    assert uuid_res == "feat-custom-1"
    assert reg.get_feature("CUSTOM_MOMENTUM") == defn
