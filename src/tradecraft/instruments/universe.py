"""Point-in-time universe membership management.

Supports querying which instruments belonged to an index (e.g. NIFTY_50)
at any historical date, with confidence tracking to prevent unverified
membership from being used in trustworthy research.

Design decisions:
- `verified_as_of` semantics: records when membership was verified, not
  when it started (unless authoritative data provides that)
- Historical queries before verified coverage return UNVERIFIED/UNKNOWN
- No arbitrary `effective_from` dates are invented
"""

import logging
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from tradecraft.core.db_models import Instrument, UniverseMembership

logger = logging.getLogger(__name__)

# Confidence levels for universe membership
VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
UNKNOWN = "UNKNOWN"


class PointInTimeUniverse:
    """Query-interface for point-in-time index membership.

    At any historical date T, `members(T)` returns the instruments
    that were members of the specified index at that date, along with
    the confidence level of that information.
    """

    def __init__(self, db_session: Session, index_name: str = "NIFTY_50"):
        self.db = db_session
        self.index_name = index_name

    def members(self, query_date: date) -> list[dict[str, Any]]:
        """Return instruments that were members at `query_date`.

        Returns a list of dicts with:
            - instrument: Instrument model
            - confidence: VERIFIED / UNVERIFIED / UNKNOWN
            - membership: UniverseMembership record
        """
        stmt = (
            select(UniverseMembership)
            .join(Instrument)
            .where(
                and_(
                    UniverseMembership.index_name == self.index_name,
                    or_(
                        UniverseMembership.effective_from.is_(None),
                        UniverseMembership.effective_from <= query_date,
                    ),
                    or_(
                        UniverseMembership.effective_to.is_(None),
                        UniverseMembership.effective_to >= query_date,
                    ),
                    Instrument.is_active == True,  # noqa: E712
                )
            )
        )
        memberships = self.db.scalars(stmt).all()

        results = []
        for m in memberships:
            results.append(
                {
                    "instrument": m.instrument,
                    "confidence": m.confidence,
                    "membership": m,
                }
            )
        return results

    def member_instruments(self, query_date: date) -> list[Instrument]:
        """Return just the Instrument objects that were members at `query_date`."""
        return [r["instrument"] for r in self.members(query_date)]

    def is_member(self, instrument_id: uuid.UUID, query_date: date) -> bool:
        """Check if an instrument was a member at `query_date`."""
        stmt = select(UniverseMembership).where(
            and_(
                UniverseMembership.index_name == self.index_name,
                UniverseMembership.instrument_id == instrument_id,
                or_(
                    UniverseMembership.effective_from.is_(None),
                    UniverseMembership.effective_from <= query_date,
                ),
                or_(
                    UniverseMembership.effective_to.is_(None),
                    UniverseMembership.effective_to >= query_date,
                ),
            )
        )
        return self.db.scalars(stmt).first() is not None

    def membership_confidence(self, query_date: date) -> str:
        """Return the weakest confidence level across all memberships at `query_date`.

        If any membership is UNKNOWN → UNKNOWN
        If any is UNVERIFIED → UNVERIFIED
        Only if all are VERIFIED → VERIFIED
        """
        members = self.members(query_date)
        if not members:
            return UNKNOWN

        confidences = {m["confidence"] for m in members}
        if UNKNOWN in confidences:
            return UNKNOWN
        if UNVERIFIED in confidences:
            return UNVERIFIED
        return VERIFIED

    def seed_current_members(
        self,
        instruments: list[Instrument],
        verified_as_of: date | None = None,
    ) -> int:
        """Seed current membership records with UNVERIFIED confidence.

        Does NOT set an arbitrary effective_from date. Uses `verified_as_of`
        to indicate when this membership information was observed.

        Returns count of new memberships created.
        """
        verified_as_of = verified_as_of or date.today()
        created = 0

        for inst in instruments:
            # Check if already has a membership record
            existing = self.db.scalars(
                select(UniverseMembership).where(
                    and_(
                        UniverseMembership.instrument_id == inst.id,
                        UniverseMembership.index_name == self.index_name,
                        UniverseMembership.effective_to.is_(None),
                    )
                )
            ).first()

            if not existing:
                membership = UniverseMembership(
                    instrument_id=inst.id,
                    index_name=self.index_name,
                    effective_from=None,  # We do NOT know the actual start date
                    effective_to=None,  # Current member (no end date)
                    source="nifty50_static_list",
                    source_reference="Current constituent list as of observation date",
                    verified_as_of=verified_as_of,
                    retrieved_at=datetime.utcnow(),
                    confidence=UNVERIFIED,
                )
                self.db.add(membership)
                created += 1

        if created > 0:
            self.db.commit()
            logger.info(
                f"Seeded {created} UNVERIFIED {self.index_name} memberships "
                f"(verified_as_of={verified_as_of})"
            )

        return created
