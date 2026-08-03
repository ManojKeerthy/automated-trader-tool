"""Strategy registry for managing immutable strategy versions (ADR-007)."""

import logging

from tradecraft.core.exceptions import StrategyError
from tradecraft.strategy.base import Strategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """In-memory and persistent registry for strategy definitions.

    Enforces that strategy versions are immutable once registered.
    """

    def __init__(self) -> None:
        self._strategies: dict[tuple[str, str], Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        """Register a strategy instance.

        Raises StrategyError if the (name, version) combination is already registered.
        """
        key = (strategy.strategy_id, strategy.version)
        if key in self._strategies:
            raise StrategyError(
                f"Strategy '{strategy.strategy_id}' version '{strategy.version}' "
                "is already registered and cannot be modified (ADR-007)."
            )
        self._strategies[key] = strategy
        logger.info(f"Registered strategy {strategy.strategy_id}-v{strategy.version}")

    def get(self, strategy_id: str, version: str) -> Strategy | None:
        """Get a strategy by ID and version."""
        return self._strategies.get((strategy_id, version))

    def list_strategies(self) -> list[dict[str, str]]:
        """List all registered strategies."""
        return [
            {
                "strategy_id": s.strategy_id,
                "name": s.name,
                "version": s.version,
                "description": s.description,
            }
            for s in self._strategies.values()
        ]
