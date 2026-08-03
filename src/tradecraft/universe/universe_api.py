"""Point-in-Time Universe API for TradeCraft Research Platform."""

from datetime import date

from tradecraft.universe.historical_membership import HistoricalMembershipEngine, MembershipRecord
from tradecraft.universe.security_master import Security, SecurityMaster
from tradecraft.universe.survivorship_guard import SurvivorshipGuard
from tradecraft.universe.universe_registry import UniverseRegistry


class UniverseAPI:
    """Unified Point-in-Time Universe API consumed by strategies and DataPortal."""

    def __init__(
        self,
        security_master: SecurityMaster,
        universe_registry: UniverseRegistry,
        membership_engine: HistoricalMembershipEngine,
    ):
        self.security_master = security_master
        self.universe_registry = universe_registry
        self.membership_engine = membership_engine
        self.survivorship_guard = SurvivorshipGuard(security_master)

    def get_constituents(self, universe_id: str, query_date: date) -> list[Security]:
        """Return Security objects belonging to universe_id on query_date."""
        sec_uuids = self.membership_engine.get_constituents(query_date, universe_id)
        securities: list[Security] = []

        for uuid_str in sec_uuids:
            # Enforce survivorship boundary check
            self.survivorship_guard.validate_security_access(uuid_str, query_date)
            sec = self.security_master.get_by_uuid(uuid_str)
            if sec:
                securities.append(sec)
        return securities

    def is_member(self, security_uuid: str, universe_id: str, query_date: date) -> bool:
        """Check if security_uuid was a constituent of universe_id on query_date."""
        self.survivorship_guard.validate_security_access(security_uuid, query_date)
        return self.membership_engine.is_member(security_uuid, universe_id, query_date)

    def security_history(self, security_uuid: str) -> list[MembershipRecord]:
        """Fetch historical universe membership records for a security."""
        return self.membership_engine.security_history(security_uuid)

    def universe_history(self, universe_id: str) -> list[MembershipRecord]:
        """Fetch historical membership records for a universe."""
        return self.membership_engine.universe_history(universe_id)

    def active_on(self, security_uuid: str, query_date: date) -> bool:
        """Check if security was active/listed on query_date."""
        sec = self.security_master.get_by_uuid(security_uuid)
        if not sec:
            return False
        return sec.is_listed_on(query_date)
