class TradeCraftError(Exception):
    """Base exception for all TradeCraft errors."""

    pass


class ConfigurationError(TradeCraftError):
    """Raised when environment variables or settings are misconfigured."""

    pass


class MarketDataError(TradeCraftError):
    """Raised when there is an issue fetching or storing market data."""

    pass


class CalendarError(MarketDataError):
    """Raised when there is a trading calendar or session logic failure."""

    pass


class ProviderError(MarketDataError):
    """Raised when an external data provider (Zerodha, NSE) fails or returns an error."""

    pass


class DataQualityError(MarketDataError):
    """Raised when incoming or stored data fails quality checks."""

    pass
