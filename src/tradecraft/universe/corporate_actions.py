"""Corporate Action Registry for TradeCraft Point-in-Time Data Architecture."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class CorporateActionRecord:
    """Timestamped corporate action affecting price adjustments or corporate status."""
    action_id: str
    security_uuid: str
    action_type: str  # SPLIT, BONUS, MERGER, DEMERGER, SYMBOL_CHANGE, NAME_CHANGE, DELISTING, RELISTING
    effective_date: date
    record_date: date | None = None
    ratio_from: int | None = None
    ratio_to: int | None = None
    amount: Decimal | None = None
    source: str = "NSE Corporate Announcements"
    details: str | None = None


class CorporateActionRegistry:
    """Registry maintaining timestamped corporate actions for all securities."""

    def __init__(self) -> None:
        self._actions: list[CorporateActionRecord] = []

    def register_action(self, action: CorporateActionRecord) -> str:
        """Register a corporate action record."""
        self._actions.append(action)
        return action.action_id

    def get_actions_for_security(
        self,
        security_uuid: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CorporateActionRecord]:
        """Fetch corporate actions for a security, optionally filtered by date range."""
        results = [a for a in self._actions if a.security_uuid == security_uuid]
        if start_date:
            results = [a for a in results if a.effective_date >= start_date]
        if end_date:
            results = [a for a in results if a.effective_date <= end_date]
        return sorted(results, key=lambda x: x.effective_date)

    def get_actions_as_of(self, query_date: date) -> list[CorporateActionRecord]:
        """Fetch all corporate actions effective on or before query_date."""
        return sorted(
            [a for a in self._actions if a.effective_date <= query_date],
            key=lambda x: x.effective_date,
        )
