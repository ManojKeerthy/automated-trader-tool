"""Survivorship & Lookahead Bias Protection Guard."""

from datetime import date
from typing import Optional
from tradecraft.universe.security_master import Security, SecurityMaster


class SurvivorshipBiasError(Exception):
    """Raised when a query violates survivorship or listing date boundaries."""
    pass


class SurvivorshipGuard:
    """Runtime guard validating queries against IPO, delisting, and historical membership boundaries."""

    def __init__(self, security_master: SecurityMaster):
        self.security_master = security_master

    def validate_security_access(self, security_uuid: str, query_date: date) -> None:
        """Validate that security_uuid was active/listed on query_date."""
        security = self.security_master.get_by_uuid(security_uuid)
        if not security:
            raise SurvivorshipBiasError(f"SURVIVORSHIP VIOLATION: Security UUID '{security_uuid}' not found in Security Master!")

        if security.listing_date and query_date < security.listing_date:
            raise SurvivorshipBiasError(
                f"SURVIVORSHIP VIOLATION: Attempted to query security '{security.current_symbol}' (UUID: {security_uuid}) "
                f"on date {query_date}, which is prior to its IPO listing date ({security.listing_date})!"
            )

        if security.delisting_date and query_date > security.delisting_date:
            raise SurvivorshipBiasError(
                f"SURVIVORSHIP VIOLATION: Attempted to query delisted security '{security.current_symbol}' (UUID: {security_uuid}) "
                f"on date {query_date}, which is after its delisting date ({security.delisting_date})!"
            )

    def validate_symbol_rename(self, symbol: str, query_date: date) -> Security:
        """Validate symbol query against historical symbol rename dates."""
        sec = self.security_master.get_by_symbol(symbol, query_date=query_date)
        if not sec:
            raise SurvivorshipBiasError(
                f"SURVIVORSHIP VIOLATION: Symbol '{symbol}' was not valid or active on historical date {query_date}!"
            )
        return sec
