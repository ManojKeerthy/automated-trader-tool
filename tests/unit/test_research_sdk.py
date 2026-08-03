"""Unit tests for Public Research SDK."""

import pytest
from tradecraft.sdk import ResearchClient, TradeCraftSDK


def test_research_sdk_client():
    client = ResearchClient()
    feats = client.list_registered_features()
    assert len(feats) == 12

    sdk = TradeCraftSDK()
    assert len(sdk.list_registered_features()) == 12
