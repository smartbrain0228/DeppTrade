from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.models import (
    SignalTriggerEnum,
    TradeSideEnum,
    TradeStatusEnum,
    User,
    UserPairStrategy,
)
from trading_bot_backend.app.services.market_data import fetch_strategy_candles
from trading_bot_backend.app.services.signal_history import create_signal_event
from trading_bot_backend.app.services.strategy import analyze_strategy
from trading_bot_backend.app.services.trade_execution import create_trade, trade_to_dict


async def get_assignment_for_user(
    db: AsyncSession,
    *,
    assignment_id: int,
    user_id: int,
) -> UserPairStrategy:
    stmt = (
        select(UserPairStrategy)
        .options(
            selectinload(UserPairStrategy.symbol),
            selectinload(UserPairStrategy.strategy),
            selectinload(UserPairStrategy.user),
        )
        .where(
            UserPairStrategy.id == assignment_id,
            UserPairStrategy.user_id == user_id,
            UserPairStrategy.is_active.is_(True),
        )
    )
    assignment = (await db.execute(stmt)).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active pair/strategy assignment not found.",
        )
    return assignment


async def analyze_assignment_signal(
    db: AsyncSession,
    *,
    user: User,
    assignment_id: int,
    htf_limit: int | None = None,
    ltf_limit: int | None = None,
    persist: bool = False,
) -> dict:
    assignment = await get_assignment_for_user(db, assignment_id=assignment_id, user_id=user.id)
    candles = fetch_strategy_candles(
        exchange=assignment.symbol.exchange,
        symbol=assignment.symbol.symbol,
        strategy_name=assignment.strategy.name,
        htf_limit=htf_limit,
        ltf_limit=ltf_limit,
    )
    analysis = analyze_strategy(
        strategy_name=assignment.strategy.name,
        htf_candles=candles["htf"],
        ltf_candles=candles["ltf"],
    )
    analysis["assignment"] = {
        "id": assignment.id,
        "user_id": assignment.user_id,
        "symbol_id": assignment.symbol_id,
        "symbol": assignment.symbol.symbol,
        "exchange": assignment.symbol.exchange,
        "strategy_id": assignment.strategy_id,
        "strategy_name": assignment.strategy.name.value,
        "risk_pct": float(assignment.risk_pct),
        "max_trades_per_day": assignment.max_trades_per_day,
    }
    if persist:
        await create_signal_event(db, analysis=analysis, trigger=SignalTriggerEnum.SCAN)
    return analysis


async def execute_assignment_signal(
    db: AsyncSession,
    *,
    user: User,
    assignment_id: int,
    quantity: Decimal,
    trade_status: TradeStatusEnum = TradeStatusEnum.PENDING,
    htf_limit: int | None = None,
    ltf_limit: int | None = None,
) -> dict:
    analysis = await analyze_assignment_signal(
        db,
        user=user,
        assignment_id=assignment_id,
        htf_limit=htf_limit,
        ltf_limit=ltf_limit,
    )
    signal = analysis["signal"]
    trade_plan = signal.get("trade_plan")

    if signal.get("status") != "READY" or trade_plan is None:
        await create_signal_event(db, analysis=analysis, trigger=SignalTriggerEnum.EXECUTE)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Signal is not executable: {signal.get('reason', 'unknown reason')}",
        )

    trade = await create_trade(
        db,
        user=user,
        symbol_id=analysis["assignment"]["symbol_id"],
        strategy_id=analysis["assignment"]["strategy_id"],
        side=TradeSideEnum(trade_plan["side"]),
        entry_price=Decimal(str(trade_plan["entry_price"])),
        stop_loss=Decimal(str(trade_plan["stop_loss"])),
        take_profit=Decimal(str(trade_plan["take_profit"])),
        quantity=quantity,
        trade_status=trade_status,
    )
    await create_signal_event(
        db,
        analysis=analysis,
        trigger=SignalTriggerEnum.EXECUTE,
        trade=trade,
    )

    return {
        "analysis": analysis,
        "trade": trade_to_dict(trade),
    }
