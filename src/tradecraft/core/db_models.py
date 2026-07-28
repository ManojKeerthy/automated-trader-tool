import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tradecraft.core.db import Base


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

    # Point-in-time Nifty 50 membership details
    nifty50_member_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    nifty50_member_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    market_bars: Mapped[list["MarketBar"]] = relationship(
        "MarketBar", back_populates="instrument", cascade="all, delete-orphan"
    )
    corporate_actions: Mapped[list["CorporateAction"]] = relationship(
        "CorporateAction", back_populates="instrument", cascade="all, delete-orphan"
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
