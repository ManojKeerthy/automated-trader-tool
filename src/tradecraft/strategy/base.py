"""Strategy interface and signal types for the backtesting engine.

Design decisions per approved amendments:
- SignalIntent does NOT include an `entry_price` field. The strategy
  specifies desired order type and trigger levels; the ExecutionSimulator
  determines the actual fill price.
- Strategies receive data exclusively through the DataPortal, which
  enforces point-in-time access. Strategies cannot query the database
  directly or access future information.
- Every strategy has a unique identifier, version, and parameters.
  Future changes produce a new version (ADR-007: immutable versions).
"""

from __future__ import annotations

import uuid  # noqa: TC003
from dataclasses import dataclass, field
from datetime import date  # noqa: TC003
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from tradecraft.backtesting.data_portal import DataPortal


# ---------------------------------------------------------------------------
# Signal types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalIntent:
    """A trading signal produced by a strategy.

    The strategy declares WHAT it wants to do. The ExecutionSimulator
    determines HOW and at WHAT PRICE it actually executes.

    Attributes:
        instrument_id: Target instrument UUID
        direction: 'BUY' (no shorting in current scope)
        order_type: 'MARKET', 'LIMIT', 'STOP'
        limit_price: Required for LIMIT orders
        stop_trigger: Required for STOP orders
        stop_loss_level: Protective stop-loss level for risk management
        target_level: Optional profit target
        quantity_hint: Suggested quantity (may be adjusted by risk hooks)
        confidence: Strategy's confidence score [0, 1]
        rationale: Human-readable explanation
        metadata: Additional signal context for audit trail
    """

    instrument_id: uuid.UUID
    direction: str = "BUY"
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP
    limit_price: Decimal | None = None
    stop_trigger: Decimal | None = None
    stop_loss_level: Decimal | None = None
    target_level: Decimal | None = None
    quantity_hint: int | None = None
    confidence: Decimal = Decimal("0.5")
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.direction != "BUY":
            raise ValueError(
                f"Only BUY direction supported in current scope, got: {self.direction}"
            )
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("LIMIT orders require limit_price")
        if self.order_type == "STOP" and self.stop_trigger is None:
            raise ValueError("STOP orders require stop_trigger")


@dataclass(frozen=True)
class ExitSignal:
    """Signal to exit an existing position.

    Attributes:
        instrument_id: Position instrument UUID
        exit_type: 'MARKET', 'LIMIT', 'STOP'
        limit_price: For limit exits
        stop_trigger: For stop exits
        reason: Why the exit is being triggered
    """

    instrument_id: uuid.UUID
    exit_type: str = "MARKET"
    limit_price: Decimal | None = None
    stop_trigger: Decimal | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Strategy protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Strategy(Protocol):
    """Abstract strategy interface.

    Strategies evaluate market data through the DataPortal and produce
    SignalIntents. They must NOT:
    - Directly mutate portfolio state
    - Directly execute orders
    - Bypass risk hooks
    - Query future data
    - Access arbitrary database history outside the DataPortal
    """

    @property
    def strategy_id(self) -> str:
        """Unique identifier for this strategy."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    def version(self) -> str:
        """Semantic version string (immutable once deployed)."""
        ...

    @property
    def description(self) -> str:
        """What this strategy does."""
        ...

    @property
    def parameters(self) -> dict[str, Any]:
        """Strategy configuration parameters (frozen)."""
        ...

    @property
    def required_history(self) -> int:
        """Number of historical bars needed before generating signals."""
        ...

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Evaluate strategy at current_date and produce signals.

        Args:
            current_date: The current simulation date (T). The strategy
                may only access data up to and including this date.
            data_portal: Point-in-time data access interface.

        Returns:
            List of SignalIntent (entries) and ExitSignal (exits).
            The engine processes these at T+1 earliest.
        """
        ...
