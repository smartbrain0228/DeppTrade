from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trading_bot_backend.app.db import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    TRADER = "TRADER"
    VIEWER = "VIEWER"


class StrategyNameEnum(str, enum.Enum):
    INTRADAY = "INTRADAY"
    SCALP = "SCALP"
    SMA_CROSS = "SMA_CROSS"
    SMC_INTRADAY = "SMC_INTRADAY"
    SMC_H4_M15 = "SMC_H4_M15"
    SMC_H1_M5 = "SMC_H1_M5"


class TradeSideEnum(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELED = "CANCELED"
    SKIPPED = "SKIPPED"


class SignalStatusEnum(str, enum.Enum):
    NO_BIAS = "NO_BIAS"
    WAITING_SWEEP = "WAITING_SWEEP"
    WAITING_MSS = "WAITING_MSS"
    WAITING_FVG = "WAITING_FVG"
    READY = "READY"


class SignalTriggerEnum(str, enum.Enum):
    SCAN = "SCAN"
    EXECUTE = "EXECUTE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="role_enum", native_enum=False),
        default=RoleEnum.TRADER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    pair_strategies: Mapped[list[UserPairStrategy]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    trades: Mapped[list[Trade]] = relationship(back_populates="user")
    signal_events: Mapped[list[SignalEvent]] = relationship(back_populates="user")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[StrategyNameEnum] = mapped_column(
        Enum(StrategyNameEnum, name="strategy_name_enum", native_enum=False),
        unique=True,
        nullable=False,
    )
    htf: Mapped[str] = mapped_column(String(10), nullable=False)
    ltf: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pair_strategies: Mapped[list[UserPairStrategy]] = relationship(
        back_populates="strategy"
    )
    trades: Mapped[list[Trade]] = relationship(back_populates="strategy")
    signal_events: Mapped[list[SignalEvent]] = relationship(back_populates="strategy")


class Symbol(Base):
    __tablename__ = "symbols"
    __table_args__ = (UniqueConstraint("exchange", "symbol", name="uq_symbol_exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    base_asset: Mapped[str] = mapped_column(String(20), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(20), nullable=False, default="USDT")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pair_strategies: Mapped[list[UserPairStrategy]] = relationship(back_populates="symbol")
    trades: Mapped[list[Trade]] = relationship(back_populates="symbol")
    signal_events: Mapped[list[SignalEvent]] = relationship(back_populates="symbol")


class UserPairStrategy(Base):
    __tablename__ = "user_pair_strategies"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol_id", "strategy_id", name="uq_user_symbol_strategy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    risk_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.00")
    )
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Multi-strategy extensions
    demo_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("100.0"), nullable=False
    )
    trade_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="pair_strategies")
    symbol: Mapped[Symbol] = relationship(back_populates="pair_strategies")
    strategy: Mapped[Strategy] = relationship(back_populates="pair_strategies")
    signal_events: Mapped[list[SignalEvent]] = relationship(back_populates="assignment")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tag: Mapped[StrategyNameEnum] = mapped_column(
        Enum(StrategyNameEnum, name="trade_tag_enum", native_enum=False), nullable=False
    )
    side: Mapped[TradeSideEnum] = mapped_column(
        Enum(TradeSideEnum, name="trade_side_enum", native_enum=False), nullable=False
    )
    status: Mapped[TradeStatusEnum] = mapped_column(
        Enum(TradeStatusEnum, name="trade_status_enum", native_enum=False),
        default=TradeStatusEnum.PENDING,
        nullable=False,
    )
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    # Multi-strategy extensions
    spot_bias: Mapped[str | None] = mapped_column(String(20), nullable=True)
    futures_bias: Mapped[str | None] = mapped_column(String(20), nullable=True)
    has_divergence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    is_be_reached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_swing_sl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="trades")
    symbol: Mapped[Symbol] = relationship(back_populates="trades")
    strategy: Mapped[Strategy] = relationship(back_populates="trades")
    signal_events: Mapped[list[SignalEvent]] = relationship(back_populates="trade")


class SignalEvent(Base):
    __tablename__ = "signal_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("user_pair_strategies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    trade_id: Mapped[int | None] = mapped_column(
        ForeignKey("trades.id", ondelete="SET NULL"), nullable=True, index=True
    )
    trigger: Mapped[SignalTriggerEnum] = mapped_column(
        Enum(SignalTriggerEnum, name="signal_trigger_enum", native_enum=False), nullable=False
    )
    signal_status: Mapped[SignalStatusEnum] = mapped_column(
        Enum(SignalStatusEnum, name="signal_status_enum", native_enum=False), nullable=False
    )
    signal_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    side: Mapped[TradeSideEnum | None] = mapped_column(
        Enum(TradeSideEnum, name="signal_side_enum", native_enum=False), nullable=True
    )
    htf_bias: Mapped[str] = mapped_column(String(20), nullable=False)
    analysis: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assignment: Mapped[UserPairStrategy] = relationship(back_populates="signal_events")
    user: Mapped[User] = relationship(back_populates="signal_events")
    symbol: Mapped[Symbol] = relationship(back_populates="signal_events")
    strategy: Mapped[Strategy] = relationship(back_populates="signal_events")
    trade: Mapped[Trade | None] = relationship(back_populates="signal_events")
