import json
import logging
import os
from datetime import date
from pathlib import Path

from tradecraft.config import settings
from tradecraft.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

SESSION_FILE = Path(settings.DATA_DIR) / ".kite_session.json"


class KiteSessionManager:
    """Manages Zerodha Kite Connect login sessions and caches access tokens."""

    def __init__(self) -> None:
        # Create data directory if it doesn't exist
        os.makedirs(settings.DATA_DIR, exist_ok=True)

    def get_login_url(self) -> str:
        """Generate the login redirect URL for the user to authenticate."""
        if not settings.KITE_API_KEY:
            raise ConfigurationError("KITE_API_KEY environment variable is not configured.")
        return f"https://kite.trade/connect/login?api_key={settings.KITE_API_KEY}&v=3"

    def get_cached_access_token(self) -> str | None:
        """Retrieve the cached access token if it is valid for today."""
        if not SESSION_FILE.exists():
            return None

        try:
            with open(SESSION_FILE) as f:
                data = json.load(f)

            cached_date_str = data.get("date")
            access_token = data.get("access_token")
            api_key = data.get("api_key")

            # Zerodha access tokens expire daily (around 6 AM).
            # We enforce that the token must be generated today (same calendar date).
            today_str = date.today().isoformat()
            if cached_date_str == today_str and access_token and api_key == settings.KITE_API_KEY:
                logger.info("Found valid cached Zerodha session for today.")
                return str(access_token)

            logger.info("Cached Zerodha session is stale or matches a different API key.")
            return None
        except Exception as e:
            logger.warning(f"Failed to read cached Zerodha session: {e}")
            return None

    def generate_new_session(self, request_token: str) -> str:
        """Exchange request token for an access token and cache it."""
        if not settings.KITE_API_KEY or not settings.KITE_API_SECRET:
            raise ConfigurationError(
                "Kite credentials KITE_API_KEY / KITE_API_SECRET are not configured."
            )

        try:
            from kiteconnect import KiteConnect

            logger.info("Exchanging request token for access token with Zerodha...")
            kite = KiteConnect(api_key=settings.KITE_API_KEY)
            session = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
            access_token = session["access_token"]

            # Cache the token
            session_data = {
                "access_token": access_token,
                "date": date.today().isoformat(),
                "api_key": settings.KITE_API_KEY,
            }

            with open(SESSION_FILE, "w") as f:
                json.dump(session_data, f, indent=4)

            logger.info(f"Successfully cached new Zerodha session at {SESSION_FILE}")
            return str(access_token)
        except Exception as e:
            raise ConfigurationError(f"Failed to generate new session with Zerodha: {e}")

    def clear_session(self) -> None:
        """Clear the cached session file."""
        if SESSION_FILE.exists():
            try:
                os.remove(SESSION_FILE)
                logger.info("Cleared cached Zerodha session.")
            except Exception as e:
                logger.warning(f"Failed to clear session file: {e}")
