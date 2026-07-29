"""Abstract News / Market Information Provider Interface.

Per M3A approved amendments:
- Interface/schema only. No uncontrolled LLM web browsing in deterministic backtests.
- Events contain source, publication timestamp, ingestion timestamp, entity/security
  mapping, classification, quality, and model version where AI processing occurs.
- No historical news may become available before publication time.
- If no provider exists, returns empty rather than fabricated data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime  # noqa: TC003
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid


@dataclass(frozen=True)
class NewsEvent:
    """A single news/market information event with point-in-time semantics.

    Attributes:
        source: Origin of the information (e.g. "NSE_ANNOUNCEMENT", "BSE_FILING", "NEWS_WIRE")
        publication_timestamp: When the information was published/released
        ingestion_timestamp: When the system ingested/processed the information
        available_from: The earliest simulation date at which this event may be used.
            Derived from publication_timestamp. Must be on or after publication date.
        headline: Brief description of the event
        entity_ids: List of instrument/entity UUIDs this event relates to
        classification: Event type (e.g. "EARNINGS", "CORPORATE_ACTION", "REGULATORY",
            "MACRO", "COMPANY_ANNOUNCEMENT")
        quality: Confidence in the event data
        model_version: If AI processing was applied, the model version used (None if raw)
        metadata: Additional structured information
    """

    source: str
    publication_timestamp: datetime
    ingestion_timestamp: datetime
    available_from: date
    headline: str = ""
    entity_ids: list[str] = field(default_factory=list)
    classification: str = "UNKNOWN"
    quality: str = "UNVERIFIED"  # VERIFIED, UNVERIFIED, AI_PROCESSED, UNAVAILABLE
    model_version: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class AbstractNewsDataProvider(ABC):
    """Abstract interface for point-in-time news/event data access.

    Implementations must enforce that events with available_from > query_date
    are NEVER returned. This prevents look-ahead bias.

    If no provider is configured, NullNewsDataProvider returns empty results.
    """

    @abstractmethod
    def get_events_as_of(
        self,
        query_date: date,
        instrument_id: uuid.UUID | None = None,
        classifications: list[str] | None = None,
    ) -> list[NewsEvent]:
        """Retrieve news events available at query_date.

        Args:
            query_date: The simulation/research date. Only events with
                available_from <= query_date are returned.
            instrument_id: Optional instrument filter. If None, returns all events.
            classifications: Optional classification filter.

        Returns:
            List of NewsEvent instances available at query_date.
        """
        ...

    @abstractmethod
    def provider_status(self) -> str:
        """Return provider status: CONFIGURED, NOT_CONFIGURED, ERROR."""
        ...


class NullNewsDataProvider(AbstractNewsDataProvider):
    """Default provider when no news source is configured.

    Returns empty results rather than fabricated data.
    Per M3A policy: if no provider exists, return unavailable.
    """

    def get_events_as_of(
        self,
        query_date: date,
        instrument_id: uuid.UUID | None = None,
        classifications: list[str] | None = None,
    ) -> list[NewsEvent]:
        return []

    def provider_status(self) -> str:
        return "NOT_CONFIGURED"
