"""Unit tests for PlatformMetadataCatalog."""

from tradecraft.research.platform_metadata_catalog import PlatformAssetNode, PlatformMetadataCatalog


def test_platform_metadata_catalog():
    cat = PlatformMetadataCatalog()
    node = PlatformAssetNode(node_id="n1", name="Dataset V1", asset_type="DATASET")
    cat.register_node(node)
    assert len(node.checksum) == 64
    assert cat.get_node("n1") == node
