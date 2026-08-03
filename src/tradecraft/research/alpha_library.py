"""Alpha Research Library & Machine-Readable Evaluation Framework."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AlphaSourceRecord:
    """Machine-readable institutional alpha source record."""

    alpha_id: str
    alpha_name: str
    category: str  # MOMENTUM, TREND, REVERSION, PATTERN, BREADTH, FACTOR, EVENT
    economic_rationale: str
    behavioural_rationale: str
    historical_evidence_strength: str  # STRONG, MODERATE, EMERGING
    holding_period: str  # DAILY, MULTI_DAY, SWING, MULTI_WEEK
    turnover: str  # HIGH, MEDIUM, LOW
    capacity: str  # HIGH, MEDIUM, LOW
    transaction_cost_sensitivity: str  # HIGH, MEDIUM, LOW
    market_dependency: str  # TRENDING, RANGING, ALL_REGIMES
    failure_regimes: list[str]
    suitable_universes: list[str]
    implementation_complexity: str  # LOW, MEDIUM, HIGH
    confidence_score: float  # 0.0 to 1.0
    references: list[str]
    academic_reading_list: list[str] = field(default_factory=list)
    common_pitfalls: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def checksum(self) -> str:
        payload = f"{self.alpha_id}:{self.alpha_name}:{self.category}:{self.economic_rationale}:{self.version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "alpha_id": self.alpha_id,
            "alpha_name": self.alpha_name,
            "category": self.category,
            "economic_rationale": self.economic_rationale,
            "behavioural_rationale": self.behavioural_rationale,
            "historical_evidence_strength": self.historical_evidence_strength,
            "holding_period": self.holding_period,
            "turnover": self.turnover,
            "capacity": self.capacity,
            "transaction_cost_sensitivity": self.transaction_cost_sensitivity,
            "market_dependency": self.market_dependency,
            "failure_regimes": self.failure_regimes,
            "suitable_universes": self.suitable_universes,
            "implementation_complexity": self.implementation_complexity,
            "confidence_score": self.confidence_score,
            "references": self.references,
            "academic_reading_list": self.academic_reading_list,
            "common_pitfalls": self.common_pitfalls,
            "checksum": self.checksum,
            "version": self.version,
            "created_at": self.created_at,
        }


class AlphaLibrary:
    """Central registry of the 20 pre-registered institutional alpha sources."""

    ALPHA_SOURCES_METADATA = [
        (
            "ALPHA-001",
            "Trend Following",
            "TREND",
            "Capitalizes on persistent medium-to-long term structural trends driven by capital flows.",
            "Anchoring bias, slow institutional capital re-allocation.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "TRENDING",
            ["RANGING", "HIGH_VOLATILITY"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-002",
            "Cross-Sectional Momentum",
            "MOMENTUM",
            "Long top-performing assets and short/avoid bottom-performing assets relative to peer universe.",
            "Under-reaction to news, herding behavior.",
            "STRONG",
            "MULTI_WEEK",
            "MEDIUM",
            "HIGH",
            "MEDIUM",
            "TRENDING",
            ["VOLATILE_REVERSAL"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-003",
            "Time-Series Momentum",
            "MOMENTUM",
            "Asset's own past return predicts its future return trajectory over a 1-12 month horizon.",
            "Disposition effect, delayed market pricing.",
            "STRONG",
            "MULTI_WEEK",
            "MEDIUM",
            "HIGH",
            "MEDIUM",
            "TRENDING",
            ["CHOPPY_SIDEWAYS"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-004",
            "Relative Strength",
            "MOMENTUM",
            "Stock performance relative to a benchmark index like NIFTY 50 or sector index.",
            "Institutional rotation toward outperforming leaders.",
            "STRONG",
            "MULTI_DAY",
            "MEDIUM",
            "HIGH",
            "MEDIUM",
            "TRENDING",
            ["HIGH_VOLATILITY"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-005",
            "Breakout",
            "PATTERN",
            "Price expansion beyond historical support or resistance levels.",
            "Stop-loss hunting, breakout buyers triggering liquidity.",
            "MODERATE",
            "MULTI_DAY",
            "HIGH",
            "MEDIUM",
            "HIGH",
            "TRENDING",
            ["FALSE_BREAKOUT_RANGING"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250"],
        ),
        (
            "ALPHA-006",
            "Volatility Compression",
            "PATTERN",
            "Periods of abnormally low volatility (squeeze) precede explosive directional expansion.",
            "Mean reversion of volatility metrics.",
            "STRONG",
            "MULTI_DAY",
            "MEDIUM",
            "MEDIUM",
            "MEDIUM",
            "TRENDING",
            ["LOW_VOLATILITY_DRIFT"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250"],
        ),
        (
            "ALPHA-007",
            "Mean Reversion",
            "REVERSION",
            "Prices temporarily deviate from intrinsic moving average fair value before returning.",
            "Overreaction to transient noise or temporary illiquidity.",
            "MODERATE",
            "SWING",
            "HIGH",
            "MEDIUM",
            "HIGH",
            "RANGING",
            ["STRONG_TRENDING"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250"],
        ),
        (
            "ALPHA-008",
            "Gap Continuation",
            "EVENT",
            "Overnight gaps caused by news drift further in the direction of the gap.",
            "Post-earnings announcement drift (PEAD).",
            "MODERATE",
            "DAILY",
            "HIGH",
            "LOW",
            "HIGH",
            "ALL_REGIMES",
            ["GAP_FADE"],
            ["NIFTY50", "NIFTY100", "NIFTY200"],
        ),
        (
            "ALPHA-009",
            "Gap Reversal",
            "REVERSION",
            "Extreme overnight gaps fade as short-term liquidity returns.",
            "Panic selling or euphoric buying at market open.",
            "MODERATE",
            "DAILY",
            "HIGH",
            "LOW",
            "HIGH",
            "RANGING",
            ["STRONG_CATALYST"],
            ["NIFTY50", "NIFTY100", "NIFTY200"],
        ),
        (
            "ALPHA-010",
            "Sector Rotation",
            "BREADTH",
            "Capital shifts across industry sectors based on macroeconomic cycle phase.",
            "Institutional sector asset re-allocation.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "TRENDING",
            ["SECTOR_DISPERSION_COLLAPSE"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-011",
            "Market Breadth",
            "BREADTH",
            "Aggregated advance-decline lines or percentage of stocks above SMA indicate true market health.",
            "Divergence between index heavyweights and broader market.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "TRENDING",
            ["NARROW_INDEX_RALLY"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-012",
            "Liquidity Expansion",
            "PATTERN",
            "Surge in daily trading volume signals institutional accumulation prior to price movement.",
            "Institutional footprint detection.",
            "STRONG",
            "SWING",
            "MEDIUM",
            "HIGH",
            "MEDIUM",
            "ALL_REGIMES",
            ["LOW_VOLUME_ILLIQUIDITY"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-013",
            "Earnings Drift",
            "EVENT",
            "Post-earnings announcement price drift continues for weeks after surprise beat.",
            "Analyst earnings estimate revision inertia.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "ALL_REGIMES",
            ["EARNINGS_REVERSAL"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-014",
            "52-Week High Effect",
            "MOMENTUM",
            "Stocks approaching 52-week high face psychological resistance, then accelerate upon breakout.",
            "Anchoring to 52-week high price point.",
            "STRONG",
            "MULTI_WEEK",
            "MEDIUM",
            "HIGH",
            "MEDIUM",
            "TRENDING",
            ["MARKET_TOP"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-015",
            "Factor Investing",
            "FACTOR",
            "Systematic exposure to persistent risk factors (Momentum, Value, Quality, Low Vol).",
            "Compensation for non-diversifiable risk or structural market constraints.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "ALL_REGIMES",
            ["FACTOR_CROWDING"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-016",
            "Quality",
            "FACTOR",
            "High profitability, low debt, and stable earnings outperform low-quality speculative stocks.",
            "Investor preference for lottery-like high beta stocks.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "ALL_REGIMES",
            ["SPECULATIVE_BUBBLE"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-017",
            "Value",
            "FACTOR",
            "Low price-to-earnings or price-to-book assets revert to intrinsic fundamental valuation.",
            "Value trap, loss aversion, analyst over-extrapolation.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "ALL_REGIMES",
            ["VALUE_TRAP_REGIME"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-018",
            "Low Volatility",
            "FACTOR",
            "Low beta / low variance stocks deliver superior risk-adjusted returns than high beta stocks.",
            "Leverage constraints and benchmark-tracking mandate incentives.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "ALL_REGIMES",
            ["HIGH_BETA_RALLY"],
            ["NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-019",
            "Small Cap",
            "FACTOR",
            "Small cap equities command a liquidity and information asymmetry risk premium.",
            "Higher illiquidity and coverage gap.",
            "MODERATE",
            "MULTI_WEEK",
            "LOW",
            "MEDIUM",
            "MEDIUM",
            "TRENDING",
            ["LIQUIDITY_CRUNCH"],
            ["NIFTY250", "NIFTY500"],
        ),
        (
            "ALPHA-020",
            "Risk Premia",
            "FACTOR",
            "Systematic capture of structural market premiums (variance premium, term structure).",
            "Compensation for bearing tail risk during market crashes.",
            "STRONG",
            "MULTI_WEEK",
            "LOW",
            "HIGH",
            "LOW",
            "ALL_REGIMES",
            ["TAIL_RISK_EVENT"],
            ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY250", "NIFTY500"],
        ),
    ]

    def __init__(self) -> None:
        self._library: dict[str, AlphaSourceRecord] = {}
        self._initialize_library()

    def _initialize_library(self) -> None:
        for (
            aid,
            name,
            cat,
            econ,
            behav,
            ev,
            hold,
            turn,
            cap,
            cost,
            mkt,
            fail,
            univ,
        ) in self.ALPHA_SOURCES_METADATA:
            record = AlphaSourceRecord(
                alpha_id=aid,
                alpha_name=name,
                category=cat,
                economic_rationale=econ,
                behavioural_rationale=behav,
                historical_evidence_strength=ev,
                holding_period=hold,
                turnover=turn,
                capacity=cap,
                transaction_cost_sensitivity=cost,
                market_dependency=mkt,
                failure_regimes=fail,
                suitable_universes=univ,
                implementation_complexity="MEDIUM",
                confidence_score=0.85,
                references=[f"Literature reference for {name}"],
                academic_reading_list=[f"Academic Paper: Foundations of {name}"],
                common_pitfalls=[f"Over-fitting parameters in {name}"],
            )
            self._library[aid] = record

    def get_alpha_source(self, alpha_id: str) -> AlphaSourceRecord | None:
        return self._library.get(alpha_id.upper())

    def list_alpha_sources(self) -> list[AlphaSourceRecord]:
        return list(self._library.values())
