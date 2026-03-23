from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.db import get_db
from trading_bot_backend.app.models import (
    SignalStatusEnum,
    SignalTriggerEnum,
    Strategy,
    StrategyNameEnum,
    Symbol,
    User,
    UserPairStrategy,
)
from trading_bot_backend.app.services.signal_history import (
    list_signal_events_admin,
    signal_event_to_admin_dict,
)
from trading_bot_backend.app.users.deps import get_current_admin

router = APIRouter(prefix="/admin-api", tags=["admin-api"])


class SymbolCreate(BaseModel):
    exchange: str = Field(min_length=2, max_length=20)
    symbol: str = Field(min_length=3, max_length=30)
    base_asset: str = Field(min_length=2, max_length=20)
    quote_asset: str = Field(default="USDT", min_length=2, max_length=20)


class UserPairStrategyAssign(BaseModel):
    user_id: int
    symbol_id: int
    strategy_id: int
    risk_pct: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0.01"), le=Decimal("5.00"))
    max_trades_per_day: int = Field(default=1, ge=1, le=50)
    is_active: bool = True


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_initial_data(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    default_strategies = [
        {"name": StrategyNameEnum.INTRADAY, "htf": "H4", "ltf": "M15"},
        {"name": StrategyNameEnum.SCALP, "htf": "H1", "ltf": "M5"},
    ]
    default_symbols = [
        {"exchange": "binance", "symbol": "SOL/USDT", "base_asset": "SOL", "quote_asset": "USDT"},
        {"exchange": "mexc", "symbol": "SOL/USDT", "base_asset": "SOL", "quote_asset": "USDT"},
        {"exchange": "mexc", "symbol": "SKR/USDT", "base_asset": "SKR", "quote_asset": "USDT"},
    ]

    created_strategies = 0
    created_symbols = 0

    for data in default_strategies:
        existing = await db.execute(select(Strategy).where(Strategy.name == data["name"]))
        if existing.scalar_one_or_none() is None:
            db.add(Strategy(**data))
            created_strategies += 1

    for data in default_symbols:
        existing = await db.execute(
            select(Symbol).where(
                Symbol.exchange == data["exchange"],
                Symbol.symbol == data["symbol"],
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(Symbol(**data))
            created_symbols += 1

    await db.commit()

    return {
        "strategies_created": created_strategies,
        "symbols_created": created_symbols,
    }


@router.get("/strategies")
async def list_strategies(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Strategy).order_by(Strategy.id.asc()))).scalars().all()
    return [
        {
            "id": row.id,
            "name": row.name.value,
            "htf": row.htf,
            "ltf": row.ltf,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.get("/users")
async def list_users(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(User).order_by(User.id.asc()))).scalars().all()
    return [
        {
            "id": row.id,
            "email": row.email,
            "username": row.username,
            "role": row.role.value,
            "is_active": row.is_active,
            "is_verified": row.is_verified,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/symbols", status_code=status.HTTP_201_CREATED)
async def create_symbol(
    payload: SymbolCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    exchange = payload.exchange.lower().strip()
    symbol = payload.symbol.upper().strip()

    existing = await db.execute(
        select(Symbol).where(Symbol.exchange == exchange, Symbol.symbol == symbol)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Symbol already exists for this exchange.",
        )

    row = Symbol(
        exchange=exchange,
        symbol=symbol,
        base_asset=payload.base_asset.upper().strip(),
        quote_asset=payload.quote_asset.upper().strip(),
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return {
        "id": row.id,
        "exchange": row.exchange,
        "symbol": row.symbol,
        "base_asset": row.base_asset,
        "quote_asset": row.quote_asset,
        "is_active": row.is_active,
    }


@router.get("/symbols")
async def list_symbols(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Symbol).order_by(Symbol.id.asc()))).scalars().all()
    return [
        {
            "id": row.id,
            "exchange": row.exchange,
            "symbol": row.symbol,
            "base_asset": row.base_asset,
            "quote_asset": row.quote_asset,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.get("/user-pair-strategies")
async def list_user_pair_strategies(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserPairStrategy)
        .options(
            selectinload(UserPairStrategy.user),
            selectinload(UserPairStrategy.symbol),
            selectinload(UserPairStrategy.strategy),
        )
        .order_by(UserPairStrategy.id.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "username": row.user.username,
            "symbol_id": row.symbol_id,
            "symbol": row.symbol.symbol,
            "exchange": row.symbol.exchange,
            "strategy_id": row.strategy_id,
            "strategy_name": row.strategy.name.value,
            "risk_pct": float(row.risk_pct),
            "max_trades_per_day": row.max_trades_per_day,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.post("/user-pair-strategies", status_code=status.HTTP_201_CREATED)
async def assign_user_pair_strategy(
    payload: UserPairStrategyAssign,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user_row = await db.execute(select(User).where(User.id == payload.user_id))
    if user_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    symbol_row = await db.execute(select(Symbol).where(Symbol.id == payload.symbol_id))
    if symbol_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found.")

    strategy_row = await db.execute(select(Strategy).where(Strategy.id == payload.strategy_id))
    strategy = strategy_row.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")

    existing_stmt = select(UserPairStrategy).where(
        UserPairStrategy.user_id == payload.user_id,
        UserPairStrategy.symbol_id == payload.symbol_id,
        UserPairStrategy.strategy_id == payload.strategy_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing:
        existing.risk_pct = payload.risk_pct
        existing.max_trades_per_day = payload.max_trades_per_day
        existing.is_active = payload.is_active
        target = existing
    else:
        target = UserPairStrategy(
            user_id=payload.user_id,
            symbol_id=payload.symbol_id,
            strategy_id=payload.strategy_id,
            risk_pct=payload.risk_pct,
            max_trades_per_day=payload.max_trades_per_day,
            is_active=payload.is_active,
        )
        db.add(target)

    await db.commit()
    await db.refresh(target)

    return {
        "id": target.id,
        "user_id": target.user_id,
        "symbol_id": target.symbol_id,
        "strategy_id": target.strategy_id,
        "strategy_name": strategy.name.value,
        "risk_pct": float(target.risk_pct),
        "max_trades_per_day": target.max_trades_per_day,
        "is_active": target.is_active,
    }


@router.get("/signal-events")
async def list_signal_events(
    assignment_id: int | None = Query(default=None, ge=1),
    user_id: int | None = Query(default=None, ge=1),
    symbol_id: int | None = Query(default=None, ge=1),
    strategy_id: int | None = Query(default=None, ge=1),
    signal_status: SignalStatusEnum | None = Query(default=None),
    trigger: SignalTriggerEnum | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total, events = await list_signal_events_admin(
        db,
        assignment_id=assignment_id,
        user_id=user_id,
        symbol_id=symbol_id,
        strategy_id=strategy_id,
        signal_status=signal_status,
        trigger=trigger,
        created_from=created_from,
        created_to=created_to,
        offset=offset,
        limit=limit,
    )
    return {
        "total": total,
        "count": len(events),
        "offset": offset,
        "limit": limit,
        "filters": {
            "assignment_id": assignment_id,
            "user_id": user_id,
            "symbol_id": symbol_id,
            "strategy_id": strategy_id,
            "signal_status": signal_status.value if signal_status is not None else None,
            "trigger": trigger.value if trigger is not None else None,
            "created_from": created_from,
            "created_to": created_to,
        },
        "items": [signal_event_to_admin_dict(event) for event in events],
    }
