"""TradeCraft Public Research SDK.

The ONLY public API interface for future research notebooks, scripts, and dashboards.
All internal engines (research, backtesting, universe, execution) remain internal.
"""

from tradecraft.sdk.research_client import ResearchClient, TradeCraftSDK

__all__ = ["ResearchClient", "TradeCraftSDK"]
