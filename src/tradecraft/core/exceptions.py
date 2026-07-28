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


# ---------------------------------------------------------------------------
# M2 — Backtesting exceptions
# ---------------------------------------------------------------------------


class BacktestError(TradeCraftError):
    """Base exception for backtesting engine failures."""

    pass


class LookAheadError(BacktestError):
    """Raised when code attempts to access data beyond the current simulation date.

    This is a critical bias-prevention mechanism. Any occurrence indicates a
    potential look-ahead bias in the strategy or data pipeline.
    """

    pass


class InsufficientCapitalError(BacktestError):
    """Raised when a trade cannot be executed due to insufficient cash."""

    pass


class ResearchQualityError(BacktestError):
    """Raised when data quality is insufficient for the requested research quality level."""

    pass


class StrategyError(TradeCraftError):
    """Raised when a strategy encounters an error during evaluation."""

    pass
