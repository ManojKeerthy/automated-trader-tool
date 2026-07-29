"""Strategy-Neutral Screening Engine.

Per M3A approved amendments:
- The screening engine is STRATEGY-NEUTRAL. It does not implement strategy-specific
  rules, entry/exit logic, or scoring algorithms.
- It orchestrates: eligibility screening → feature computation → regime classification
  → produces a ScreeningResult with metadata.
- Explicitly supports zero-candidate/no-trade output (empty result is valid).
- Does not impose minimum-candidate requirements.
- Does not fabricate historical Nifty membership.
- Records all metadata needed for reproducibility: config versions, feature versions,
  regime version, universe quality, eligibility exclusion summary.
"""

from __future__ import annotations

import logging
import uuid  # noqa: TC003
from dataclasses import dataclass, field
from datetime import date  # noqa: TC003
from typing import Any

from tradecraft.screening.eligibility import (
    EligibilityConfig,
    EligibilityScreen,
    InstrumentData,
)
from tradecraft.screening.regime import (
    MarketRegimeEngine,
    MarketRegimeSnapshot,
    RegimeDefinition,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScreeningCandidate:
    """A single instrument that passed eligibility screening.

    Contains the instrument_id and computed features available for downstream
    strategy-specific analysis. No strategy scoring is applied here.
    """

    instrument_id: uuid.UUID
    symbol: str
    features: dict[str, float | None] = field(default_factory=dict)
    research_quality_flags: list[str] = field(default_factory=list)


@dataclass
class ScreeningResult:
    """Complete result of a screening run.

    Contains all metadata required for reproducibility and downstream processing.
    Zero candidates is a valid and expected result.
    """

    screen_date: date
    screening_version: str
    eligibility_config_version: str
    liquidity_config_version: str
    regime_definition_version: str
    feature_versions: dict[str, str] = field(default_factory=dict)

    # Core outputs
    regime: MarketRegimeSnapshot | None = None
    candidates: list[ScreeningCandidate] = field(default_factory=list)

    # Metadata for audit
    total_universe: int = 0
    eligible_count: int = 0
    excluded_count: int = 0
    exclusion_summary: dict[str, int] = field(default_factory=dict)
    research_quality_warnings: list[str] = field(default_factory=list)
    execution_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    def is_empty(self) -> bool:
        """An empty screening result is valid — no candidates passed eligibility."""
        return len(self.candidates) == 0


@dataclass(frozen=True)
class ScreeningConfig:
    """Configuration for the screening engine."""

    version: str = "screening_v1.0"
    eligibility: EligibilityConfig = EligibilityConfig()
    regime: RegimeDefinition = RegimeDefinition()
    compute_features: bool = True
    compute_regime: bool = True


class ScreeningEngine:
    """Strategy-neutral screening engine.

    Orchestrates eligibility, feature computation, and regime classification
    WITHOUT implementing any strategy-specific logic.

    The engine's job is to produce a ScreeningResult containing:
    1. Which securities are eligible (and why others aren't)
    2. Market regime snapshot
    3. Computed features for eligible securities

    Strategy-specific scoring, ranking, and signal generation happen downstream
    in M3B/M3C strategy modules.
    """

    def __init__(self, config: ScreeningConfig | None = None):
        self.config = config or ScreeningConfig()
        self.eligibility_screen = EligibilityScreen(self.config.eligibility)
        self.regime_engine = MarketRegimeEngine(self.config.regime)

    def run(
        self,
        screen_date: date,
        instruments: list[InstrumentData],
        instrument_features: dict[uuid.UUID, dict[str, float | None]] | None = None,
        benchmark_close: Any | None = None,
        benchmark_high: Any | None = None,
        benchmark_low: Any | None = None,
        constituent_closes: dict[str, Any] | None = None,
        universe_verified: bool = True,
    ) -> ScreeningResult:
        """Run the complete screening pipeline.

        Args:
            screen_date: Point-in-time date for screening.
            instruments: Pre-loaded instrument data.
            instrument_features: Pre-computed features per instrument.
            benchmark_close: Benchmark closing prices for regime classification.
            benchmark_high: Benchmark high prices for regime volatility.
            benchmark_low: Benchmark low prices for regime volatility.
            constituent_closes: Dict of constituent close series for breadth.
            universe_verified: Whether universe membership is verified for screen_date.

        Returns:
            ScreeningResult with candidates, regime, and metadata.
            Zero candidates is a valid result.
        """
        cfg = self.config
        result = ScreeningResult(
            screen_date=screen_date,
            screening_version=cfg.version,
            eligibility_config_version="eligibility_v1.0",
            liquidity_config_version=cfg.eligibility.liquidity.version,
            regime_definition_version=cfg.regime.version,
        )

        # Step 1: Eligibility screening
        eligibility_result = self.eligibility_screen.screen(screen_date, instruments)
        result.total_universe = eligibility_result.total_universe
        result.eligible_count = eligibility_result.eligible_count
        result.excluded_count = eligibility_result.exclusion_count
        result.exclusion_summary = eligibility_result.exclusion_summary()

        # Propagate research quality warnings
        for rq in eligibility_result.research_quality_flags:
            result.research_quality_warnings.append(f"{rq.symbol}: {rq.reason_code} — {rq.detail}")

        # Step 2: Market regime classification (if configured)
        if cfg.compute_regime and benchmark_close is not None:
            try:
                result.regime = self.regime_engine.classify(
                    observation_date=screen_date,
                    benchmark_close=benchmark_close,
                    benchmark_high=benchmark_high,
                    benchmark_low=benchmark_low,
                    constituent_closes=constituent_closes,
                    universe_verified=universe_verified,
                )
            except Exception as e:
                logger.warning(f"Regime classification failed: {e}")
                result.research_quality_warnings.append(f"Regime classification failed: {e}")

        # Step 3: Build candidates from eligible instruments
        instrument_map = {inst.instrument_id: inst for inst in instruments}
        features = instrument_features or {}

        for inst_id in eligibility_result.eligible_instruments:
            inst = instrument_map.get(inst_id)
            if inst is None:
                continue

            inst_features = features.get(inst_id, {})

            # Collect research quality flags for this instrument
            rq_flags = [
                rq.reason_code
                for rq in eligibility_result.research_quality_flags
                if rq.instrument_id == inst_id
            ]

            candidate = ScreeningCandidate(
                instrument_id=inst_id,
                symbol=inst.symbol,
                features=inst_features,
                research_quality_flags=rq_flags,
            )
            result.candidates.append(candidate)

        logger.info(
            f"Screening {screen_date}: {result.candidate_count} candidates "
            f"from {result.total_universe} universe "
            f"(regime: {result.regime.trend if result.regime else 'N/A'})"
        )

        return result
