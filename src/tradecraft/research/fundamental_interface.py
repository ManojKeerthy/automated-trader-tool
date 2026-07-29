"""Abstract Fundamental Data Provider Interface.

Per M3A approved amendments:
- Interface/schema only. No unreliable scraping.
- Observations contain metric, value, financial period, publication timestamp,
  available_from, source, and quality/confidence.
- Historical access must obey available_from <= simulation/query time.
- If no trusted provider exists, returns unavailable/no observation rather than
  fabricated placeholder values.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date  # noqa: TC003
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid


@dataclass(frozen=True)
class FundamentalObservation:
    """A single fundamental data observation with point-in-time semantics.

    Attributes:
        metric: The fundamental metric name (e.g. "revenue", "eps", "roe")
        value: The numeric value of the observation
        financial_period: The financial reporting period (e.g. "Q1FY2026", "FY2025")
        publication_date: When this information was published/made available publicly
        available_from: The earliest simulation date at which this observation may be used.
            Must be >= publication_date. Historical access must obey: query_date >= available_from.
        source: Data source identifier (e.g. "NSE_FILING", "ANNUAL_REPORT", "PROVIDER_X")
        quality: Confidence level of the observation
    """

    metric: str
    value: float | None
    financial_period: str
    publication_date: date
    available_from: date
    source: str
    quality: str = "UNVERIFIED"  # VERIFIED, UNVERIFIED, ESTIMATED, UNAVAILABLE


class AbstractFundamentalDataProvider(ABC):
    """Abstract interface for point-in-time fundamental data access.

    Implementations must enforce that observations with available_from > query_date
    are NEVER returned. This prevents look-ahead bias in historical research.

    If no trusted provider is configured, the default NullFundamentalDataProvider
    returns empty results rather than fabricating data.
    """

    @abstractmethod
    def get_fundamentals_as_of(
        self,
        instrument_id: uuid.UUID,
        query_date: date,
        metrics: list[str] | None = None,
    ) -> list[FundamentalObservation]:
        """Retrieve fundamental observations available at query_date.

        Args:
            instrument_id: The instrument to query.
            query_date: The simulation/research date. Only observations with
                available_from <= query_date are returned.
            metrics: Optional list of specific metrics to retrieve.
                If None, returns all available metrics.

        Returns:
            List of FundamentalObservation instances available at query_date.
            Empty list if no data is available.
        """
        ...

    @abstractmethod
    def get_latest_observation(
        self,
        instrument_id: uuid.UUID,
        metric: str,
        query_date: date,
    ) -> FundamentalObservation | None:
        """Retrieve the most recent observation of a specific metric as of query_date.

        Returns None if no observation is available.
        """
        ...

    @abstractmethod
    def provider_status(self) -> str:
        """Return provider status: CONFIGURED, NOT_CONFIGURED, ERROR."""
        ...


class NullFundamentalDataProvider(AbstractFundamentalDataProvider):
    """Default provider when no fundamental data source is configured.

    Returns empty/unavailable results rather than fabricated data.
    Per M3A policy: if no trusted provider exists, return unavailable.
    """

    def get_fundamentals_as_of(
        self,
        instrument_id: uuid.UUID,
        query_date: date,
        metrics: list[str] | None = None,
    ) -> list[FundamentalObservation]:
        return []

    def get_latest_observation(
        self,
        instrument_id: uuid.UUID,
        metric: str,
        query_date: date,
    ) -> FundamentalObservation | None:
        return None

    def provider_status(self) -> str:
        return "NOT_CONFIGURED"
