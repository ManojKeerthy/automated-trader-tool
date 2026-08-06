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
        max_holding_days: Time stop in trading sessions, ENFORCED BY THE ENGINE
        quantity_hint: Suggested quantity (may be adjusted by risk hooks)
        confidence: Strategy's confidence score [0, 1]
        rationale: Human-readable explanation
        metadata: Additional signal context for audit trail

    EXIT COMPLETENESS (defect F3, fixed 2026-08-06)
    ==============================================
    Every entry must declare how it intends to leave. Before this fix no Cycle 1 strategy
    emitted an ExitSignal or a target_level, and `max_holding_days` was buried in
    `metadata` where nothing read it. The only exits that could fire were STOP_LOSS and the
    end-of-backtest force close, which mechanically produced a ~10-14% win rate with an
    ~11x payoff ratio across all four "independent" strategy families. That was one
    artifact observed four times, not four findings.

    `max_holding_days` is now a first-class field that the engine enforces, and
    `__post_init__` rejects any signal that declares no exit path at all.
    See docs/research/REPO_AUDIT_2026-08-06.md §3.
    """

    instrument_id: uuid.UUID
    direction: str = "BUY"
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP
    limit_price: Decimal | None = None
    stop_trigger: Decimal | None = None
    stop_loss_level: Decimal | None = None
    target_level: Decimal | None = None
    max_holding_days: int | None = None
    quantity_hint: int | None = None
    confidence: Decimal = Decimal("0.5")
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    # Escape hatch for genuine buy-and-hold benchmarks, which legitimately have no exit.
    # Must be set deliberately; it exists so that "no exit" is always an explicit choice
    # rather than an omission that silently turns a strategy into a hold.
    intentional_buy_and_hold: bool = False

    def __post_init__(self) -> None:
        if self.direction != "BUY":
            raise ValueError(
                f"Only BUY direction supported in current scope, got: {self.direction}"
            )
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("LIMIT orders require limit_price")
        if self.order_type == "STOP" and self.stop_trigger is None:
            raise ValueError("STOP orders require stop_trigger")

        has_exit = (
            self.stop_loss_level is not None
            or self.target_level is not None
            or self.max_holding_days is not None
        )
        if not has_exit and not self.intentional_buy_and_hold:
            raise ValueError(
                "SignalIntent declares no exit path: stop_loss_level, target_level and "
                "max_holding_days are all None. A position that can only be closed by the "
                "end-of-backtest force close is not a strategy - that configuration produced "
                "a ~10-14% win rate with an ~11x payoff across all four Cycle 1 families. "
                "Set at least one exit, or pass intentional_buy_and_hold=True if this really "
                "is a hold benchmark. See REPO_AUDIT_2026-08-06 section 3."
            )
        if self.max_holding_days is not None and self.max_holding_days < 1:
            raise ValueError(f"max_holding_days must be >= 1, got {self.max_holding_days}")


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
