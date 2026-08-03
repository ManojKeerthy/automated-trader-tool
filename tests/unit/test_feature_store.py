"""Unit tests for FeatureStore."""

import pytest
from tradecraft.research.feature_store import FeatureStore


def test_feature_store_caching():
    store = FeatureStore()
    key = store.store_feature_value(
        feature_name="RSI",
        security_uuid="sec-1",
        observation_date="2020-01-15",
        value=42.5,
    )
    assert len(key) == 64
    val = store.get_feature_value("RSI", "sec-1", "2020-01-15")
    assert val == 42.5

    missing = store.get_feature_value("RSI", "sec-2", "2020-01-15")
    assert missing is None
