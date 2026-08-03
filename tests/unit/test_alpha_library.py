"""Unit tests for AlphaLibrary and AlphaSourceRecord."""

import pytest
from tradecraft.research.alpha_library import AlphaLibrary, AlphaSourceRecord


def test_alpha_library_initialization():
    lib = AlphaLibrary()
    sources = lib.list_alpha_sources()
    assert len(sources) == 20
    
    alpha1 = lib.get_alpha_source("ALPHA-001")
    assert alpha1 is not None
    assert alpha1.alpha_name == "Trend Following"
    assert alpha1.category == "TREND"
    assert len(alpha1.checksum) == 64
