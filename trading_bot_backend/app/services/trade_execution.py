from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.models import (
    Strategy,
    Symbol,
    Trade,
    TradeSideEnum,
    TradeStatusEnum,
    User,
    UserPairStrategy,
)

MAX_TOTAL_ACTIVE_RISK_PCT = Decimal("2.00")
ACTIVE_TRADE_STATUSES = (TradeStatusEnum.PENDING, TradeStatusEnum.OPEN)
VALID_STATUS_TRANSITIONS = {
    TradeStatusEnum.PENDING: {TradeStatusEnum.OPEN, TradeStatusEnum.CANCELED, TradeStatusEnum.CLOSED},
    TradeStatusEnum.OPEN: {TradeStatusEnum.CLOSED, TradeStatusEnum.CANCELED},
    TradeStatusEnum.CLOSED: set(),
    TradeStatusEnum.CANCELED: set(),
}


def trade_to_dict(trade: Trade) -> dict:
    return {
        "id": trade.id,
        "user_id": trade.user_id,
        "symbol_id": trade.symbol_id,
        "symbol": trade.symbol.symbol,
        "exchange": trade.symbol.exchange,
        "strategy_id": trade.strategy_id,
        "strategy_name": trade.strategy.name.value,
        "tag": trade.tag.value,
        "side": trade.side.value,
        "status": trade.status.value,
        "entry_price": float(trade.entry_price),
        "stop_loss": float(trade.stop_loss),
        "take_profit": float(trade.take_profit),
        "quantity": float(trade.quantity),
        "pnl": float(trade.pnl) if trade.pnl is not None else None,
        "is_be_reached": trade.is_be_reached,
        "last_swing_sl": float(trade.last_swing_sl) if trade.last_swing_sl is not None else None,
        "opened_at": trade.opened_at,
        "closed_at": trade.closed_at,
    }


def normalize_closed_at(trade: Trade, closed_at: datetime) -> datetime:
    if trade.opened_at is not None and closed_at < trade.opened_at:
        return trade.opened_at
    return closed_at


def validate_trade_levels(
    *,
    entry_price: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    side: TradeSideEnum,
) -> None:
    if side == TradeSideEnum.BUY:
        if stop_loss >= entry_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="For BUY trades, stop_loss must be below entry_price.",
            )
        if take_profit <= entry_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="For BUY trades, take_profit must be above entry_price.",
            )
    else:
        if stop_loss <= entry_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="For SELL trades, stop_loss must be above entry_price.",
            )
        if take_profit >= entry_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="For SELL trades, take_profit must be below entry_price.",
            )


def assert_valid_status_transition(current: TradeStatusEnum, next_status: TradeStatusEnum) -> None:
    if next_status == current:
        return
    if next_status not in VALID_STATUS_TRANSITIONS[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid trade status transition: {current.value} -> {next_status.value}.",
        )


async def get_trade_for_user(db: AsyncSession, trade_id: int, user_id: int) -> Trade | None:
    stmt = (
        select(Trade)
        .options(selectinload(Trade.symbol), selectinload(Trade.strategy))
        .where(Trade.id == trade_id, Trade.user_id == user_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_daily_trade_count(
    db: AsyncSession,
    *,
    user_id: int,
    symbol_id: int,
    strategy_id: int,
) -> int:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.count(Trade.id)).where(
        Trade.user_id == user_id,
        Trade.symbol_id == symbol_id,
        Trade.strategy_id == strategy_id,
        Trade.status != TradeStatusEnum.CANCELED,
        Trade.opened_at >= start_of_day,
    )
    return (await db.execute(stmt)).scalar_one()


async def get_active_risk_pct(db: AsyncSession, *, user_id: int) -> Decimal:
    stmt = (
        select(func.coalesce(func.sum(UserPairStrategy.risk_pct), 0))
        .select_from(Trade)
        .join(
            UserPairStrategy,
            (
                (UserPairStrategy.user_id == Trade.user_id)
                & (UserPairStrategy.symbol_id == Trade.symbol_id)
                & (UserPairStrategy.strategy_id == Trade.strategy_id)
            ),
        )
        .where(
            Trade.user_id == user_id,
            Trade.status.in_(ACTIVE_TRADE_STATUSES),
            UserPairStrategy.is_active.is_(True),
        )
    )
    value = (await db.execute(stmt)).scalar_one()
    return value if isinstance(value, Decimal) else Decimal(str(value))


async def list_user_trades(
    db: AsyncSession,
    *,
    user_id: int,
    status_filter: TradeStatusEnum | None = None,
    limit: int = 50,
) -> list[Trade]:
    stmt: Select[tuple[Trade]] = (
        select(Trade)
        .options(selectinload(Trade.symbol), selectinload(Trade.strategy))
        .where(Trade.user_id == user_id)
        .order_by(Trade.opened_at.desc())
        .limit(limit)
    )
    if status_filter is not None:
        stmt = stmt.where(Trade.status == status_filter)

    return (await db.execute(stmt)).scalars().all()


async def create_trade(
    db: AsyncSession,
    *,
    user: User,
    symbol_id: int,
    strategy_id: int,
    side: TradeSideEnum,
    entry_price: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    quantity: Decimal,
    trade_status: TradeStatusEnum,
) -> Trade:
    mapping_stmt = select(UserPairStrategy).where(
        UserPairStrategy.user_id == user.id,
        UserPairStrategy.symbol_id == symbol_id,
        UserPairStrategy.strategy_id == strategy_id,
        UserPairStrategy.is_active.is_(True),
    )
    mapping = (await db.execute(mapping_stmt)).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active pair/strategy assignment found for this user.",
        )

    validate_trade_levels(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        side=side,
    )

    strategy = (await db.execute(select(Strategy).where(Strategy.id == strategy_id))).scalar_one_or_none()
    if strategy is None or not strategy.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")

    symbol = (await db.execute(select(Symbol).where(Symbol.id == symbol_id))).scalar_one_or_none()
    if symbol is None or not symbol.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found.")

    today_trade_count = await get_daily_trade_count(
        db,
        user_id=user.id,
        symbol_id=symbol_id,
        strategy_id=strategy_id,
    )
    if today_trade_count >= mapping.max_trades_per_day:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Daily trade limit reached for this pair/strategy assignment.",
        )

    active_risk_pct = await get_active_risk_pct(db, user_id=user.id)
    if trade_status in ACTIVE_TRADE_STATUSES and active_risk_pct + mapping.risk_pct > MAX_TOTAL_ACTIVE_RISK_PCT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active account risk limit exceeded.",
        )

    trade = Trade(
        user_id=user.id,
        symbol_id=symbol_id,
        strategy_id=strategy_id,
        tag=strategy.name,
        side=side,
        status=trade_status,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        quantity=quantity,
    )
    db.add(trade)
    await db.commit()

    stmt = (
        select(Trade)
        .options(selectinload(Trade.symbol), selectinload(Trade.strategy))
        .where(Trade.id == trade.id)
    )
    return (await db.execute(stmt)).scalar_one()


async def update_trade(
    db: AsyncSession,
    *,
    trade: Trade,
    status_value: TradeStatusEnum | None = None,
    stop_loss: Decimal | None = None,
    take_profit: Decimal | None = None,
    pnl: Decimal | None = None,
    closed_at: datetime | None = None,
) -> Trade:
    if stop_loss is not None or take_profit is not None:
        validate_trade_levels(
            entry_price=trade.entry_price,
            stop_loss=stop_loss or trade.stop_loss,
            take_profit=take_profit or trade.take_profit,
            side=trade.side,
        )

    if status_value is not None:
        assert_valid_status_transition(trade.status, status_value)
        trade.status = status_value
        if status_value == TradeStatusEnum.CLOSED and closed_at is None and trade.closed_at is None:
            trade.closed_at = normalize_closed_at(trade, datetime.now(timezone.utc))
        elif status_value == TradeStatusEnum.CANCELED:
            trade.closed_at = normalize_closed_at(trade, datetime.now(timezone.utc))

    if stop_loss is not None:
        trade.stop_loss = stop_loss
    if take_profit is not None:
        trade.take_profit = take_profit
    if pnl is not None:
        trade.pnl = pnl
    if closed_at is not None:
        trade.closed_at = normalize_closed_at(trade, closed_at)

    await db.commit()
    await db.refresh(trade)

    stmt = (
        select(Trade)
        .options(selectinload(Trade.symbol), selectinload(Trade.strategy))
        .where(Trade.id == trade.id)
    )
    return (await db.execute(stmt)).scalar_one()
