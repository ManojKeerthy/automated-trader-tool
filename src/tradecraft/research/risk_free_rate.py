"""Versioned and configurable risk-free rate management for research.

Reference: 91-day Government of India Treasury Bill yield (sourcing from RBI/CCIL).
Current verified rate as of July 2026: ~5.35% per annum.

Per approved amendments:
Every backtest must record:
- annual risk-free rate used
- source
- observation / effective date
- retrieval date where applicable
- whether the value is HISTORICAL_POINT_IN_TIME or CURRENT_RATE_ASSUMPTION
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class RiskFreeRateConfig:
    """Configurable risk-free rate model with provenance tracking."""

    annual_rate: Decimal = Decimal("5.35")  # Latest verified 91-day GoI T-Bill rate (July 2026)
    source: str = "RBI / CCIL 91-day Treasury Bill Yield"
    observation_date: date = date(2026, 7, 27)
    retrieval_date: date = date(2026, 7, 28)
    rate_type: str = (
        "CURRENT_RATE_ASSUMPTION"  # HISTORICAL_POINT_IN_TIME or CURRENT_RATE_ASSUMPTION
    )

    def to_dict(self) -> dict[str, str]:
        return {
            "annual_rate_pct": str(self.annual_rate),
            "source": self.source,
            "observation_date": self.observation_date.isoformat(),
            "retrieval_date": self.retrieval_date.isoformat(),
            "rate_type": self.rate_type,
        }
