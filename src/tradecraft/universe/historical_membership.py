"""Historical Membership Engine for Point-in-Time Universe Architecture."""

from dataclasses import dataclass
from datetime import date


@dataclass
class MembershipRecord:
    """Effective-dated index membership record for a security."""
    security_uuid: str
    universe_id: str
    effective_from: date
    effective_to: date | None = None
    source: str = "NSE Official Changes"
    confidence: str = "VERIFIED"  # VERIFIED, UNVERIFIED, UNKNOWN


class HistoricalMembershipEngine:
    """Query engine for point-in-time universe membership."""

    def __init__(self) -> None:
        self._records: list[MembershipRecord] = []

    def add_membership_record(self, record: MembershipRecord) -> None:
        """Add an effective-dated membership record."""
        self._records.append(record)

    def get_constituents(self, query_date: date, universe_id: str = "NIFTY50") -> list[str]:
        """Return security_uuids belonging to universe_id on query_date. Zero survivorship bias."""
        universe_id_upper = universe_id.upper()
        constituents: set[str] = set()

        for rec in self._records:
            if rec.universe_id.upper() == universe_id_upper and rec.effective_from <= query_date and (rec.effective_to is None or query_date <= rec.effective_to):
                constituents.add(rec.security_uuid)
        return sorted(list(constituents))

    def is_member(self, security_uuid: str, universe_id: str, query_date: date) -> bool:
        """Check if security_uuid was a constituent of universe_id on query_date."""
        constituents = self.get_constituents(query_date, universe_id)
        return security_uuid in constituents

    def security_history(self, security_uuid: str) -> list[MembershipRecord]:
        """Return all historical membership records for a security_uuid."""
        return [r for r in self._records if r.security_uuid == security_uuid]

    def universe_history(self, universe_id: str) -> list[MembershipRecord]:
        """Return all historical membership records for a universe_id."""
        u_upper = universe_id.upper()
        return [r for r in self._records if r.universe_id.upper() == u_upper]
