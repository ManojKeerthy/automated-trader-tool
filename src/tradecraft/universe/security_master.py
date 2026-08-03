"""Security Master Catalog for TradeCraft Point-in-Time Universe Architecture.

Decouples strategy logic from ticker symbols by enforcing immutable security_uuid keys.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class SymbolHistoryRecord:
    """Historical symbol change record for a security."""
    effective_from: date
    effective_to: Optional[date]
    old_symbol: Optional[str]
    new_symbol: str
    change_reason: str = "RENAME"


@dataclass
class Security:
    """Immutable security entity with symbol history and ISIN mapping."""
    security_uuid: str
    current_symbol: str
    name: str
    isin: Optional[str] = None
    exchange: str = "NSE"
    segment: str = "EQ"
    sector: Optional[str] = None
    industry: Optional[str] = None
    listing_date: Optional[date] = None
    delisting_date: Optional[date] = None
    is_active: bool = True
    aliases: List[str] = field(default_factory=list)
    symbol_history: List[SymbolHistoryRecord] = field(default_factory=list)
    bse_symbol_history: List[SymbolHistoryRecord] = field(default_factory=list)

    def get_symbol_on(self, query_date: date) -> str:
        """Return the active NSE symbol for this security on a specific historical date."""
        if not self.symbol_history:
            return self.current_symbol

        for rec in sorted(self.symbol_history, key=lambda x: x.effective_from, reverse=True):
            if rec.effective_from <= query_date:
                if rec.effective_to is None or query_date <= rec.effective_to:
                    return rec.new_symbol
        return self.current_symbol

    def is_listed_on(self, query_date: date) -> bool:
        """Check if security was active/listed on query_date."""
        if self.listing_date and query_date < self.listing_date:
            return False
        if self.delisting_date and query_date > self.delisting_date:
            return False
        return True


class SecurityMaster:
    """Primary Security Master catalog mapping symbols & ISINs to security_uuid."""

    def __init__(self) -> None:
        self._securities: Dict[str, Security] = {}  # security_uuid -> Security
        self._symbol_map: Dict[str, str] = {}  # current_symbol -> security_uuid
        self._isin_map: Dict[str, str] = {}  # ISIN -> security_uuid

    def register_security(self, security: Security) -> str:
        """Register a security entity into the Security Master."""
        self._securities[security.security_uuid] = security
        self._symbol_map[security.current_symbol.upper()] = security.security_uuid
        if security.isin:
            self._isin_map[security.isin.upper()] = security.security_uuid
        return security.security_uuid

    def get_by_uuid(self, security_uuid: str) -> Optional[Security]:
        """Retrieve Security entity by security_uuid."""
        return self._securities.get(security_uuid)

    def get_by_symbol(self, symbol: str, query_date: Optional[date] = None) -> Optional[Security]:
        """Retrieve Security entity by symbol, optionally resolving historical symbol changes."""
        symbol_upper = symbol.upper()

        # Check current symbol map first
        if symbol_upper in self._symbol_map:
            sec = self._securities[self._symbol_map[symbol_upper]]
            if query_date is None or sec.is_listed_on(query_date):
                return sec

        # Search symbol history records
        for sec in self._securities.values():
            for rec in sec.symbol_history:
                if rec.new_symbol.upper() == symbol_upper or (rec.old_symbol and rec.old_symbol.upper() == symbol_upper):
                    if query_date is None or (rec.effective_from <= query_date and (rec.effective_to is None or query_date <= rec.effective_to)):
                        return sec
        return None

    def get_by_isin(self, isin: str) -> Optional[Security]:
        """Retrieve Security entity by ISIN."""
        sec_uuid = self._isin_map.get(isin.upper())
        return self._securities.get(sec_uuid) if sec_uuid else None

    def all_securities(self) -> List[Security]:
        """Return all registered Security entities."""
        return list(self._securities.values())
