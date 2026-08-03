"""Unit tests for UniverseRegistry and UniverseDefinition."""

import pytest
from tradecraft.universe.universe_registry import UniverseDefinition, UniverseRegistry


def test_universe_registry_canonical_initialization():
    reg = UniverseRegistry()
    universes = reg.list_universes()
    uids = [u.universe_id for u in universes]
    assert "NIFTY50" in uids
    assert "NIFTY250" in uids
    assert "NIFTY500" in uids


def test_universe_definition_checksum():
    def1 = UniverseDefinition(
        universe_id="NIFTY250",
        name="NSE NIFTY 250 Index",
        version="1.0.0",
        dataset_version="v1",
    )
    assert len(def1.checksum) == 64
