import logging

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from tradecraft.core.exceptions import ConfigurationError

logger = logging.getLogger("tradecraft.preflight")


def validate_database_schema(session: Session) -> None:
    """Preflight database validation to check if the schema matches the application models."""
    logger.info("Running database preflight validation...")
    try:
        engine = session.bind
        if engine is None:
            raise ConfigurationError("Database session is not bound to an engine.")

        inspector = inspect(engine)

        # Check if tables exist
        tables = inspector.get_table_names()
        required_tables = ["instruments", "market_bars", "corporate_actions"]

        for table in required_tables:
            if table not in tables:
                raise ConfigurationError(
                    "DATABASE MIGRATION REQUIRED\n"
                    f"The table '{table}' does not exist in the database.\n"
                    "The application schema is newer than the database.\n\n"
                    "Run:\n"
                    "alembic upgrade head"
                )

        # Check if transformation_version column exists in market_bars
        columns = [col["name"] for col in inspector.get_columns("market_bars")]
        if "transformation_version" not in columns:
            raise ConfigurationError(
                "DATABASE MIGRATION REQUIRED\n"
                "The column 'transformation_version' does not exist in the 'market_bars' table.\n"
                "The application schema is newer than the database.\n\n"
                "Run:\n"
                "alembic upgrade head"
            )

        logger.info("Database preflight validation successful. Schema is up to date.")
    except ConfigurationError:
        raise
    except Exception as e:
        logger.warning(f"Database preflight check encountered an unexpected error: {e}")
