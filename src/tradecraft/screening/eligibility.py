"""Eligibility & Liquidity Screening Pipeline.

Per M3A approved amendments:
- Separates OPERATIONAL eligibility from RESEARCH quality classification.
- LiquidityScreenConfig makes thresholds configurable and records version/threshold
  used in screening metadata.
- Default ₹5 Crore average daily traded value is a PROVISIONAL configurable research
  default, not an industry-standard or validated optimal threshold.
- Architects for eventual position-size/liquidity participation consideration.
- Securities excluded by operational eligibility cannot be screened.
- Securities passing operational eligibility but with research-quality limitations
  (e.g. UNVERIFIED universe) can still be screened for RESEARCH_ONLY experiments.

Pipeline:
    UNIVERSE → DATA_QUALITY → TRADABILITY → LIQUIDITY → EXCLUSIONS → ELIGIBLE_UNIVERSE
"""

from __future__ import annotations

import logging
import uuid  # noqa: TC003
from dataclasses import dataclass, field
from datetime import date  # noqa: TC003

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exclusion reason codes
# ---------------------------------------------------------------------------

INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
STALE_DATA = "STALE_DATA"
LOW_LIQUIDITY = "LOW_LIQUIDITY"
CORPORATE_ACTION_UNRESOLVED = "CORPORATE_ACTION_UNRESOLVED"
UNVERIFIED_IDENTITY = "UNVERIFIED_IDENTITY"
PRICE_DATA_INVALID = "PRICE_DATA_INVALID"
UNVERIFIED_UNIVERSE = "UNVERIFIED_UNIVERSE"
ZERO_VOLUME = "ZERO_VOLUME"


@dataclass(frozen=True)
class ExclusionRecord:
    """Reason why a security was excluded from the eligible universe."""

    instrument_id: uuid.UUID
    symbol: str
    reason_code: str
    detail: str = ""
    is_operational: bool = True  # True = operational exclusion, False = research-quality flag


@dataclass(frozen=True)
class LiquidityScreenConfig:
    """Configurable liquidity screening parameters.

    The default ₹5 Crore (50,000,000 INR) 20-session average traded value threshold
    is a PROVISIONAL configurable research default. M3B may later test sensitivity.

    Architecture supports eventual position-size/liquidity participation by including
    max_participation_pct: the maximum fraction of average daily volume a single
    position should consume.
    """

    version: str = "v1.0_provisional"
    min_avg_traded_value: float = 50_000_000.0  # ₹5 Crore
    avg_traded_value_period: int = 20  # sessions
    min_avg_volume: float = 0.0  # optional minimum average volume
    min_price: float = 0.0  # optional minimum share price
    max_participation_pct: float = 0.0  # 0 = not enforced yet; eventual position-size check


@dataclass(frozen=True)
class EligibilityConfig:
    """Configuration for the full eligibility screening pipeline."""

    min_history_bars: int = 200  # Minimum bars of history required for a security
    max_stale_days: int = 5  # Maximum days since last bar before flagging as stale
    liquidity: LiquidityScreenConfig = LiquidityScreenConfig()
    excluded_symbols: list[str] = field(default_factory=list)  # Project-level exclusions


@dataclass
class EligibilityResult:
    """Result of running the eligibility screen on a universe."""

    screen_date: date
    config_version: str
    liquidity_config_version: str
    total_universe: int
    eligible_instruments: list[uuid.UUID] = field(default_factory=list)
    excluded_instruments: list[ExclusionRecord] = field(default_factory=list)
    research_quality_flags: list[ExclusionRecord] = field(default_factory=list)

    @property
    def eligible_count(self) -> int:
        return len(self.eligible_instruments)

    @property
    def exclusion_count(self) -> int:
        return len(self.excluded_instruments)

    def exclusion_summary(self) -> dict[str, int]:
        """Count exclusions by reason code."""
        summary: dict[str, int] = {}
        for exc in self.excluded_instruments:
            summary[exc.reason_code] = summary.get(exc.reason_code, 0) + 1
        return summary


@dataclass
class InstrumentData:
    """Lightweight instrument data container for screening (no DB dependency)."""

    instrument_id: uuid.UUID
    symbol: str
    is_active: bool
    total_bars: int
    earliest_date: date | None
    latest_date: date | None
    latest_close: float | None
    avg_traded_value_20: float | None  # pre-computed feature
    avg_volume_20: float | None  # pre-computed feature
    has_unresolved_corporate_actions: bool = False
    identity_verified: bool = True
    universe_verified: bool = True  # Whether PIT universe membership is verified


class EligibilityScreen:
    """Deterministic point-in-time eligibility screening pipeline.

    Pipeline:
        UNIVERSE → DATA_QUALITY → TRADABILITY → LIQUIDITY → EXCLUSIONS → ELIGIBLE_UNIVERSE

    Separates:
    A. Operational/data eligibility — securities that CAN be processed
    B. Research-quality flags — limitations that affect evidence quality but
       do not prevent processing (propagated downstream)
    """

    def __init__(self, config: EligibilityConfig | None = None):
        self.config = config or EligibilityConfig()

    def screen(
        self,
        screen_date: date,
        instruments: list[InstrumentData],
    ) -> EligibilityResult:
        """Run the full eligibility pipeline on a set of instruments.

        Args:
            screen_date: The point-in-time date for screening.
            instruments: Pre-loaded instrument data with computed features.

        Returns:
            EligibilityResult with eligible/excluded instruments and research quality flags.
        """
        result = EligibilityResult(
            screen_date=screen_date,
            config_version="eligibility_v1.0",
            liquidity_config_version=self.config.liquidity.version,
            total_universe=len(instruments),
        )

        for inst in instruments:
            exclusion = self._check_operational_eligibility(screen_date, inst)
            if exclusion is not None:
                result.excluded_instruments.append(exclusion)
                continue

            # Research quality flags (non-blocking but propagated)
            rq_flags = self._check_research_quality(inst)
            result.research_quality_flags.extend(rq_flags)

            result.eligible_instruments.append(inst.instrument_id)

        logger.info(
            f"Eligibility screen {screen_date}: "
            f"{result.eligible_count}/{result.total_universe} eligible, "
            f"{result.exclusion_count} excluded"
        )
        return result

    def _check_operational_eligibility(
        self, screen_date: date, inst: InstrumentData
    ) -> ExclusionRecord | None:
        """Check operational/data eligibility (blocking exclusions)."""
        cfg = self.config

        # 1. Data quality: minimum history
        if inst.total_bars < cfg.min_history_bars:
            return ExclusionRecord(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                reason_code=INSUFFICIENT_HISTORY,
                detail=f"Has {inst.total_bars} bars, need {cfg.min_history_bars}",
            )

        # 2. Data quality: stale data
        if inst.latest_date is not None:
            days_stale = (screen_date - inst.latest_date).days
            if days_stale > cfg.max_stale_days:
                return ExclusionRecord(
                    instrument_id=inst.instrument_id,
                    symbol=inst.symbol,
                    reason_code=STALE_DATA,
                    detail=f"Last bar {inst.latest_date}, {days_stale} days stale",
                )

        # 3. Data quality: invalid price data
        if inst.latest_close is not None and inst.latest_close <= 0:
            return ExclusionRecord(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                reason_code=PRICE_DATA_INVALID,
                detail=f"Latest close is {inst.latest_close}",
            )

        # 4. Tradability: zero volume
        if inst.avg_volume_20 is not None and inst.avg_volume_20 <= 0:
            return ExclusionRecord(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                reason_code=ZERO_VOLUME,
                detail="Average 20-day volume is zero",
            )

        # 5. Liquidity: average traded value
        liq = cfg.liquidity
        if (
            inst.avg_traded_value_20 is not None
            and liq.min_avg_traded_value > 0
            and inst.avg_traded_value_20 < liq.min_avg_traded_value
        ):
            return ExclusionRecord(
                    instrument_id=inst.instrument_id,
                    symbol=inst.symbol,
                    reason_code=LOW_LIQUIDITY,
                    detail=(
                        f"Avg traded value ₹{inst.avg_traded_value_20:,.0f} "
                        f"< threshold ₹{liq.min_avg_traded_value:,.0f}"
                    ),
                )

        # 6. Corporate actions
        if inst.has_unresolved_corporate_actions:
            return ExclusionRecord(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                reason_code=CORPORATE_ACTION_UNRESOLVED,
                detail="Unresolved corporate actions pending",
            )

        # 7. Identity verification
        if not inst.identity_verified:
            return ExclusionRecord(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                reason_code=UNVERIFIED_IDENTITY,
                detail="Instrument identity not verified",
            )

        # 8. Project-level exclusions
        if inst.symbol in cfg.excluded_symbols:
            return ExclusionRecord(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                reason_code="PROJECT_EXCLUSION",
                detail="Excluded by project configuration",
            )

        return None

    def _check_research_quality(self, inst: InstrumentData) -> list[ExclusionRecord]:
        """Check research-quality flags (non-blocking but propagated)."""
        flags: list[ExclusionRecord] = []

        if not inst.universe_verified:
            flags.append(
                ExclusionRecord(
                    instrument_id=inst.instrument_id,
                    symbol=inst.symbol,
                    reason_code=UNVERIFIED_UNIVERSE,
                    detail="Point-in-time universe membership not verified for this instrument",
                    is_operational=False,
                )
            )

        return flags
