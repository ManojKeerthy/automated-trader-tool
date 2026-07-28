import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from tradecraft.core.exceptions import ProviderError

logger = logging.getLogger(__name__)


class MarketDataProvider(Protocol):
    """Abstract interface for downloading market price data."""

    def get_daily_bars(
        self, symbol: str, exchange: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch daily OHLCV bars for a given symbol and exchange."""
        ...

    def fetch_all_instruments(self) -> list[dict[str, Any]]:
        """Fetch master list of all tradable instruments."""
        ...


class CorporateActionsProvider(Protocol):
    """Abstract interface for downloading corporate actions (splits, bonuses, etc.)."""

    def get_corporate_actions(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch corporate actions for a given symbol."""
        ...


class TestMarketDataProvider:
    """Mock/Fixture market data provider for unit testing and offline development."""

    def __init__(
        self,
        mock_bars: list[dict[str, Any]] | None = None,
        mock_instruments: list[dict[str, Any]] | None = None,
    ):
        self.mock_bars = mock_bars or []
        self.mock_instruments = mock_instruments or []

    def get_daily_bars(
        self, symbol: str, exchange: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        # Filter mock bars matching constraints
        result = []
        for bar in self.mock_bars:
            b_date = bar["trading_date"]
            if isinstance(b_date, str):
                b_date = date.fromisoformat(b_date)

            if (
                bar["symbol"] == symbol
                and bar["exchange"] == exchange
                and start_date <= b_date <= end_date
            ):
                # Copy to prevent mutation
                bar_copy = dict(bar)
                bar_copy["trading_date"] = b_date
                result.append(bar_copy)
        return result

    def fetch_all_instruments(self) -> list[dict[str, Any]]:
        return self.mock_instruments


class TestCorporateActionsProvider:
    """Mock/Fixture corporate actions provider for testing."""

    def __init__(self, mock_actions: list[dict[str, Any]] | None = None):
        self.mock_actions = mock_actions or []

    def get_corporate_actions(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        result = []
        for act in self.mock_actions:
            ex_dt = act["ex_date"]
            if isinstance(ex_dt, str):
                ex_dt = date.fromisoformat(ex_dt)

            if act["symbol"] == symbol and start_date <= ex_dt <= end_date:
                act_copy = dict(act)
                act_copy["ex_date"] = ex_dt
                if "record_date" in act_copy and isinstance(act_copy["record_date"], str):
                    act_copy["record_date"] = date.fromisoformat(act_copy["record_date"])
                result.append(act_copy)
        return result


class ZerodhaMarketDataProvider:
    """Kite Connect historical API data provider."""

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self._kite: Any = None
        self._initialized = False

    def _init_client(self) -> None:
        if self._initialized:
            return
        try:
            from kiteconnect import KiteConnect

            self._kite = KiteConnect(api_key=self.api_key)
            self._kite.set_access_token(self.access_token)
            self._initialized = True
        except Exception as e:
            raise ProviderError(f"Failed to initialize Kite client: {e}")

    def fetch_all_instruments(self) -> list[dict[str, Any]]:
        self._init_client()
        try:
            logger.info("Fetching instruments from Zerodha...")
            # Fetch all instruments. Returns list of dicts.
            instruments = self._kite.instruments()
            return [
                {
                    "symbol": inst["tradingsymbol"],
                    "exchange": inst["exchange"],
                    "isin": inst.get("isin"),
                    "name": inst.get("name"),
                    "segment": inst.get("segment"),
                    "tick_size": Decimal(str(inst["tick_size"])),
                    "lot_size": int(inst["lot_size"]),
                    "instrument_token": int(inst["instrument_token"]),
                    "is_active": True,
                }
                for inst in instruments
            ]
        except Exception as e:
            raise ProviderError(f"Zerodha failed to fetch instruments: {e}")

    def get_daily_bars(
        self, symbol: str, exchange: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        self._init_client()
        try:
            # We first need to get the instrument token.
            # Usually, instruments are cached locally. But for raw API calls,
            # we need to find it from the instruments list.
            # To avoid doing this on every single query, we expect the caller
            # to pass instrument_token in additional context or do mapping.
            # To support the protocol cleanly, we can lookup, but it is slow.
            # Instead, we will support passing instrument_token directly
            # by fetching instruments once and caching, or via custom param.
            # Let's cache the mapping of (exchange, symbol) -> token.
            raise NotImplementedError(
                "Use ZerodhaMarketDataProvider with pre-mapped instrument tokens."
            )
        except Exception as e:
            raise ProviderError(f"Failed to fetch historical data for {symbol}: {e}")

    def get_daily_bars_by_token(
        self, token: int, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        self._init_client()
        try:
            # Format dates to string "YYYY-MM-DD"
            from_str = start_date.strftime("%Y-%m-%d")
            to_str = end_date.strftime("%Y-%m-%d")

            logger.info(f"Fetching daily bars for token {token} from {from_str} to {to_str}")
            records = self._kite.historical_data(
                instrument_token=token, from_date=from_str, to_date=to_str, interval="day"
            )
            return [
                {
                    "trading_date": r["date"].date()
                    if isinstance(r["date"], datetime)
                    else datetime.strptime(r["date"][:10], "%Y-%m-%d").date(),
                    "open": Decimal(str(r["open"])),
                    "high": Decimal(str(r["high"])),
                    "low": Decimal(str(r["low"])),
                    "close": Decimal(str(r["close"])),
                    "volume": int(r["volume"]),
                    "source": "zerodha",
                    "retrieved_at": datetime.utcnow(),
                }
                for r in records
            ]
        except Exception as e:
            raise ProviderError(f"Zerodha historical API error: {e}")


class NSECorporateActionsProvider:
    """NSE website/circular corporate actions scraper/fetcher."""

    def __init__(self) -> None:
        pass

    def get_corporate_actions(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        # For M1, scraping NSE is highly fragile due to Cloudflare protection and changes.
        # We will log the request, and return empty list or fallback to test fixtures.
        # In a real environment, this would hit the official NSE JSON endpoint if available
        # or parse downloaded reports.
        logger.warning(
            "NSE Scraper not fully active due to access restrictions. Falling back to empty actions."
        )
        return []
