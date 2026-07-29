import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tradecraft.core.db import Base

# Dialect-portable JSON type (JSONB on PostgreSQL, JSON on SQLite/others)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


# ---------------------------------------------------------------------------
# M1 Models
# ---------------------------------------------------------------------------


class Instrument(Base):
    """Securities master catalog listing all tradeable instruments."""

    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, default="NSE")
    segment: Mapped[str] = mapped_column(String(20), nullable=False, default="EQ")
    tick_size: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0.05")
    )
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    instrument_token: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Point-in-time Nifty 50 membership details (legacy — prefer universe_membership)
    nifty50_member_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    nifty50_member_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # M2: Classification columns
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    market_bars: Mapped[list["MarketBar"]] = relationship(
        "MarketBar", back_populates="instrument", cascade="all, delete-orphan"
    )
    corporate_actions: Mapped[list["CorporateAction"]] = relationship(
        "CorporateAction", back_populates="instrument", cascade="all, delete-orphan"
    )
    history_records: Mapped[list["InstrumentHistory"]] = relationship(
        "InstrumentHistory", back_populates="instrument", cascade="all, delete-orphan"
    )
    universe_memberships: Mapped[list["UniverseMembership"]] = relationship(
        "UniverseMembership", back_populates="instrument", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("exchange", "symbol", name="uq_exchange_symbol"),)

    def __repr__(self) -> str:
        return f"<Instrument(symbol={self.symbol}, exchange={self.exchange}, is_active={self.is_active})>"


class MarketBar(Base):
    """Daily OHLCV market observations (raw and action-adjusted)."""

    __tablename__ = "market_bars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    is_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    adjustment_factor: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("1.000000")
    )
    transformation_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="market_bars")

    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "trading_date", "is_adjusted", name="uq_instrument_date_adj"
        ),
    )

    def __repr__(self) -> str:
        return f"<MarketBar(symbol={self.instrument.symbol if self.instrument else self.instrument_id}, date={self.trading_date}, close={self.close}, is_adjusted={self.is_adjusted})>"


class CorporateAction(Base):
    """Historical corporate actions (splits, dividends, etc.) affecting prices."""

    __tablename__ = "corporate_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SPLIT, BONUS, DIVIDEND, etc.
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ratio_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratio_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="corporate_actions"
    )

    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "action_type", "ex_date", name="uq_instrument_action_date"
        ),
    )

    def __repr__(self) -> str:
        return f"<CorporateAction(symbol={self.instrument.symbol if self.instrument else self.instrument_id}, type={self.action_type}, ex_date={self.ex_date})>"


# ---------------------------------------------------------------------------
# M2 Models — Instrument Identity & Universe
# ---------------------------------------------------------------------------


class InstrumentHistory(Base):
    """Tracks symbol changes, mergers, demergers and restructurings for instrument identity."""

    __tablename__ = "instrument_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    old_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SYMBOL_CHANGE, MERGER, DEMERGER, DELISTING
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="UNVERIFIED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="history_records"
    )


class UniverseMembership(Base):
    """Point-in-time index/universe membership with confidence tracking.

    Uses `verified_as_of` semantics rather than arbitrary effective dates.
    Historical queries before verified coverage should return UNVERIFIED/UNKNOWN.
    """

    __tablename__ = "universe_membership"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    index_name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "NIFTY_50"
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNVERIFIED"
    )  # VERIFIED, UNVERIFIED, UNKNOWN
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="universe_memberships"
    )


# ---------------------------------------------------------------------------
# M2 Models — Strategy & Research
# ---------------------------------------------------------------------------


class StrategyDefinition(Base):
    """Immutable strategy version record per ADR-007."""

    __tablename__ = "strategy_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    module_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="IDEA")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_strategy_name_version"),
    )

    def __repr__(self) -> str:
        return f"<StrategyDefinition(name={self.name}, version={self.version}, stage={self.lifecycle_stage})>"


class Experiment(Base):
    """Research experiment tracking for overfitting defense."""

    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    strategy_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)

    # Relationships
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(
        "BacktestRun", back_populates="experiment"
    )


class CostSchedule(Base):
    """Effective-dated transaction cost schedule with source provenance."""

    __tablename__ = "cost_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, default="NSE")
    segment: Mapped[str] = mapped_column(String(20), nullable=False, default="EQ_DELIVERY")
    schedule_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    source_references: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("version", "exchange", "segment", name="uq_cost_schedule_version"),
    )


class BacktestRun(Base):
    """Complete record of a single backtest execution for reproducibility."""

    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True
    )
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    universe: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cost_model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    slippage_model: Mapped[str] = mapped_column(String(100), nullable=False)
    benchmark: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_free_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    risk_free_rate_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    risk_free_rate_observation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    risk_free_rate_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CURRENT_RATE_ASSUMPTION"
    )
    data_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    calendar_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    research_quality: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED"
    )  # TRUSTWORTHY, RESEARCH_ONLY, UNVERIFIED, BLOCKED
    warnings: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RUNNING")
    run_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    experiment: Mapped["Experiment | None"] = relationship(
        "Experiment", back_populates="backtest_runs"
    )
    trades: Mapped[list["BacktestTrade"]] = relationship(
        "BacktestTrade", back_populates="run", cascade="all, delete-orphan"
    )
    metrics: Mapped[list["BacktestMetric"]] = relationship(
        "BacktestMetric", back_populates="run", cascade="all, delete-orphan"
    )


class BacktestTrade(Base):
    """Individual trade record within a backtest run for full audit trail."""

    __tablename__ = "backtest_trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    instrument_symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_pnl: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    total_fees: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    slippage_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    net_pnl: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    holding_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fees_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)

    # Relationships
    run: Mapped["BacktestRun"] = relationship("BacktestRun", back_populates="trades")


class BacktestMetric(Base):
    """Individual computed metric for a backtest run."""

    __tablename__ = "backtest_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    metric_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    metric_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)

    # Relationships
    run: Mapped["BacktestRun"] = relationship("BacktestRun", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("run_id", "metric_name", name="uq_run_metric"),
    )


# ---------------------------------------------------------------------------
# M3A Models — Screening & Feature Framework
# ---------------------------------------------------------------------------


class FeatureDefinitionModel(Base):
    """Persistent record of feature definitions used in screening/research.

    Stores the versioned metadata of each feature to ensure reproducibility.
    """

    __tablename__ = "feature_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    family: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    required_lookback: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_series: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    availability: Mapped[str] = mapped_column(String(30), nullable=False, default="IMMEDIATE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_feature_name_version"),
    )


class MarketRegimeSnapshotModel(Base):
    """Persistent record of market regime classifications.

    Each row captures the regime classification for a specific date using
    a specific regime definition version.
    """

    __tablename__ = "market_regime_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    regime_version: Mapped[str] = mapped_column(String(50), nullable=False)
    trend: Mapped[str] = mapped_column(String(20), nullable=False)
    volatility: Mapped[str] = mapped_column(String(20), nullable=False)
    breadth: Mapped[str] = mapped_column(String(20), nullable=False)
    trend_quality: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPUTED")
    volatility_quality: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPUTED")
    breadth_quality: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPUTED")
    overall_quality: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPUTED")
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("observation_date", "regime_version", name="uq_regime_date_version"),
    )


class ScreeningRunModel(Base):
    """Persistent record of screening run metadata.

    Captures all configuration, results summary, and quality information
    for reproducibility and audit.
    """

    __tablename__ = "screening_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    screen_date: Mapped[date] = mapped_column(Date, nullable=False)
    screening_version: Mapped[str] = mapped_column(String(50), nullable=False)
    eligibility_config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    liquidity_config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    regime_definition_version: Mapped[str] = mapped_column(String(50), nullable=False)
    total_universe: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regime_trend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    regime_volatility: Mapped[str | None] = mapped_column(String(20), nullable=True)
    regime_breadth: Mapped[str | None] = mapped_column(String(20), nullable=True)
    regime_overall_quality: Mapped[str | None] = mapped_column(String(30), nullable=True)
    exclusion_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    research_quality_warnings: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    feature_versions: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    execution_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
