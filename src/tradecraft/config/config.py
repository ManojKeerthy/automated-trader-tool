from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    # Application Mode: PAPER or LIVE
    TRADECRAFT_MODE: str = "PAPER"

    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "tradecraft"
    POSTGRES_USER: str = "tradecraft"
    POSTGRES_PASSWORD: str = "secret"  # Default fallback, should be set in .env

    # Separate database for the integration test suite. Must never equal POSTGRES_DB:
    # tests/integration/test_db_postgres.py runs Base.metadata.drop_all() against whatever
    # this resolves to, at both setup and teardown. Pointed at the real research database
    # (2026-08-06 incident), it silently destroyed the ingested market data twice in one
    # session. Same Postgres instance, different database name - full namespace isolation.
    POSTGRES_TEST_DB: str = "tradecraft_test"

    # Database URL helper
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def test_database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_TEST_DB}"

    # Zerodha Kite Connect credentials
    KITE_API_KEY: str | None = None
    KITE_API_SECRET: str | None = None

    # AI monthly budget in INR
    AI_MONTHLY_BUDGET_INR: int = 2500

    # Logging and Data Paths
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = str(BASE_DIR / "logs")
    DATA_DIR: str = str(BASE_DIR / "data")

    # Timezone settings (always Asia/Kolkata for Indian markets)
    MARKET_TIMEZONE: str = "Asia/Kolkata"

    # SettingsConfigDict specifies env file loading
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate settings
settings = Settings()
