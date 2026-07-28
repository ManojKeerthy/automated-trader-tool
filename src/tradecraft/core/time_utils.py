from datetime import date, datetime
from zoneinfo import ZoneInfo

# Market timezone constant
MARKET_TZ = ZoneInfo("Asia/Kolkata")
UTC_TZ = ZoneInfo("UTC")


def now_in_market_tz() -> datetime:
    """Get the current time in the market timezone (Asia/Kolkata)."""
    return datetime.now(MARKET_TZ)


def to_market_tz(dt: datetime) -> datetime:
    """Convert any timezone-aware datetime to market timezone (Asia/Kolkata)."""
    if dt.tzinfo is None:
        # Assume UTC if naive, or handle safely
        return dt.replace(tzinfo=UTC_TZ).astimezone(MARKET_TZ)
    return dt.astimezone(MARKET_TZ)


def to_utc(dt: datetime) -> datetime:
    """Convert any timezone-aware datetime to UTC for database storage."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MARKET_TZ).astimezone(UTC_TZ)
    return dt.astimezone(UTC_TZ)


def combine_date_time_market(d: date, t_str: str) -> datetime:
    """Combine a date and a time string (HH:MM:SS) in market timezone."""
    h, m, s = map(int, t_str.split(":"))
    dt_naive = datetime(d.year, d.month, d.day, h, m, s)
    return dt_naive.replace(tzinfo=MARKET_TZ)
