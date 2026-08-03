"""Data Vendor Abstraction Layer for TradeCraft.

Provides a vendor-agnostic interface (DataProvider) decoupling market data ingestion
and storage from specific data vendors (Zerodha, NSE, Polygon, AlphaVantage, CSV, Local DB).
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid


class DataProvider(ABC):
    """Abstract base interface for market data providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the data provider."""
        pass

    @abstractmethod
    def fetch_daily_bars(
        self,
        security_uuid: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """Fetch daily OHLCV bars for a security within date range."""
        pass

    @abstractmethod
    def fetch_instrument_metadata(self, security_uuid: str) -> Optional[Dict[str, Any]]:
        """Fetch instrument metadata (symbol, name, listing date, sector, ISIN)."""
        pass

    @abstractmethod
    def fetch_corporate_actions(self, security_uuid: str) -> List[Dict[str, Any]]:
        """Fetch corporate action records for a security."""
        pass


class LocalProvider(DataProvider):
    """Data provider interfacing with local PostgreSQL / SQLite database."""

    def __init__(self, provider_id: str = "LOCAL_DB"):
        self._id = provider_id

    @property
    def provider_name(self) -> str:
        return self._id

    def fetch_daily_bars(
        self,
        security_uuid: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        # Mock/Interface implementation for local data
        return []

    def fetch_instrument_metadata(self, security_uuid: str) -> Optional[Dict[str, Any]]:
        return {"security_uuid": security_uuid, "provider": self.provider_name}

    def fetch_corporate_actions(self, security_uuid: str) -> List[Dict[str, Any]]:
        return []


class ZerodhaProvider(LocalProvider):
    """Data provider for Zerodha Kite Connect API daily bars."""

    def __init__(self) -> None:
        super().__init__(provider_id="ZERODHA_KITE")


class NSEProvider(LocalProvider):
    """Data provider for official National Stock Exchange (NSE) historical data."""

    def __init__(self) -> None:
        super().__init__(provider_id="NSE_OFFICIAL")


class PolygonProvider(LocalProvider):
    """Data provider for Polygon.io API."""

    def __init__(self) -> None:
        super().__init__(provider_id="POLYGON_IO")


class AlphaVantageProvider(LocalProvider):
    """Data provider for AlphaVantage API."""

    def __init__(self) -> None:
        super().__init__(provider_id="ALPHA_VANTAGE")


class CSVProvider(LocalProvider):
    """Data provider ingesting local CSV files."""

    def __init__(self, data_directory: str = "data/csv") -> None:
        super().__init__(provider_id="CSV_FILE_INGESTOR")
        self.data_directory = data_directory
