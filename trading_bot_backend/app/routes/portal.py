from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.db import get_db
from trading_bot_backend.app.models import (
    Symbol,
    Trade,
    TradeStatusEnum,
    UserPairStrategy,
)
from trading_bot_backend.app.config import settings
from trading_bot_backend.app.users.deps import get_current_user

router = APIRouter(prefix="/me", tags=["portal"])
ACTIVE_TRADE_STATUSES = (TradeStatusEnum.PENDING, TradeStatusEnum.OPEN)
MAX_TOTAL_ACTIVE_RISK_PCT = Decimal("2.00")


@router.get("/overview")
async def get_my_overview(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_id = current_user.id
    open_closed_stmt = select(
        func.count(case((Trade.status == TradeStatusEnum.OPEN, 1))).label("open_count"),
        func.count(case((Trade.status == TradeStatusEnum.CLOSED, 1))).label("closed_count"),
        func.coalesce(func.sum(case((Trade.status == TradeStatusEnum.CLOSED, Trade.pnl), else_=0)), 0).label("closed_pnl"),
    ).where(Trade.user_id == current_user_id)
    open_closed_result = await db.execute(open_closed_stmt)
    open_count, closed_count, closed_pnl = open_closed_result.one()

    pair_stmt = (
        select(Symbol.symbol, Symbol.exchange, UserPairStrategy.is_active)
        .join(UserPairStrategy, UserPairStrategy.symbol_id == Symbol.id)
        .where(UserPairStrategy.user_id == current_user_id)
    )
    pair_rows = (await db.execute(pair_stmt)).all()

    active_pairs = [
        {"symbol": symbol, "exchange": exchange}
        for symbol, exchange, is_active in pair_rows
        if is_active
    ]
    inactive_pairs = [
        {"symbol": symbol, "exchange": exchange}
        for symbol, exchange, is_active in pair_rows
        if not is_active
    ]

    recent_trades_stmt = (
        select(
            Trade.id,
            Trade.tag,
            Trade.side,
            Trade.status,
            Trade.entry_price,
            Trade.stop_loss,
            Trade.take_profit,
            Trade.quantity,
            Trade.pnl,
            Trade.opened_at,
            Trade.closed_at,
            Symbol.symbol,
            Symbol.exchange,
        )
        .join(Symbol, Symbol.id == Trade.symbol_id)
        .where(Trade.user_id == current_user_id)
        .order_by(Trade.opened_at.desc())
        .limit(20)
    )
    recent_rows = (await db.execute(recent_trades_stmt)).all()

    recent_trades = []
    for row in recent_rows:
        recent_trades.append(
            {
                "trade_id": row.id,
                "tag": row.tag.value,
                "side": row.side.value,
                "status": row.status.value,
                "entry_price": float(row.entry_price),
                "stop_loss": float(row.stop_loss),
                "take_profit": float(row.take_profit),
                "quantity": float(row.quantity),
                "pnl": float(row.pnl) if row.pnl is not None else None,
                "symbol": row.symbol,
                "exchange": row.exchange,
                "opened_at": row.opened_at,
                "closed_at": row.closed_at,
            }
        )

    active_risk_stmt = (
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
            Trade.user_id == current_user_id,
            Trade.status.in_(ACTIVE_TRADE_STATUSES),
            UserPairStrategy.is_active.is_(True),
        )
    )
    active_risk_value = (await db.execute(active_risk_stmt)).scalar_one()
    active_risk_pct = (
        float(active_risk_value)
        if isinstance(active_risk_value, Decimal)
        else float(Decimal(str(active_risk_value)))
    )

    return {
        "user_id": current_user_id,
        "open_trades_count": open_count,
        "closed_trades_count": closed_count,
        "closed_pnl": float(closed_pnl) if isinstance(closed_pnl, Decimal) else closed_pnl,
        "active_risk_pct": active_risk_pct,
        "max_total_active_risk_pct": float(MAX_TOTAL_ACTIVE_RISK_PCT),
        "active_pairs": active_pairs,
        "completed_pairs": inactive_pairs,
        "recent_trades": recent_trades,
        "runtime": {
            "app_env": settings.app_env,
            "market_data_mode": settings.market_data_mode,
            "worker_enabled": settings.should_start_worker,
            "demo_engine_enabled": settings.should_start_demo_engine,
            "telegram_configured": bool(
                settings.telegram_bot_token and settings.telegram_chat_id
            ),
        },
    }


@router.get("/pair-strategies")
async def get_my_pair_strategies(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserPairStrategy)
        .options(
            selectinload(UserPairStrategy.symbol),
            selectinload(UserPairStrategy.strategy),
        )
        .where(UserPairStrategy.user_id == current_user.id)
        .order_by(UserPairStrategy.id.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": row.id,
            "symbol": row.symbol.symbol,
            "exchange": row.symbol.exchange,
            "strategy_name": row.strategy.name.value,
            "htf": row.strategy.htf,
            "ltf": row.strategy.ltf,
            "risk_pct": float(row.risk_pct),
            "max_trades_per_day": row.max_trades_per_day,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]
