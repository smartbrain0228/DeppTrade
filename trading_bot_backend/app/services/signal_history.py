from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.models import (
    SignalEvent,
    SignalStatusEnum,
    SignalTriggerEnum,
    Trade,
    TradeSideEnum,
)


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _apply_signal_event_filters(
    stmt: Select,
    *,
    assignment_id: int | None = None,
    user_id: int | None = None,
    symbol_id: int | None = None,
    strategy_id: int | None = None,
    signal_status: SignalStatusEnum | None = None,
    trigger: SignalTriggerEnum | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> Select:
    if assignment_id is not None:
        stmt = stmt.where(SignalEvent.assignment_id == assignment_id)
    if user_id is not None:
        stmt = stmt.where(SignalEvent.user_id == user_id)
    if symbol_id is not None:
        stmt = stmt.where(SignalEvent.symbol_id == symbol_id)
    if strategy_id is not None:
        stmt = stmt.where(SignalEvent.strategy_id == strategy_id)
    if signal_status is not None:
        stmt = stmt.where(SignalEvent.signal_status == signal_status)
    if trigger is not None:
        stmt = stmt.where(SignalEvent.trigger == trigger)
    if created_from is not None:
        stmt = stmt.where(SignalEvent.created_at >= created_from)
    if created_to is not None:
        stmt = stmt.where(SignalEvent.created_at <= created_to)
    return stmt


async def create_signal_event(
    db: AsyncSession,
    *,
    analysis: dict,
    trigger: SignalTriggerEnum,
    trade: Trade | None = None,
) -> SignalEvent:
    assignment = analysis["assignment"]
    signal = analysis["signal"]
    side = trade.side if trade is not None else (
        TradeSideEnum(signal["side"]) if signal.get("side") else None
    )
    event = SignalEvent(
        assignment_id=assignment["id"],
        user_id=assignment["user_id"],
        symbol_id=assignment["symbol_id"],
        strategy_id=assignment["strategy_id"],
        trade_id=trade.id if trade is not None else None,
        trigger=trigger,
        signal_status=SignalStatusEnum(signal["status"]),
        signal_reason=signal["reason"],
        side=side,
        htf_bias=analysis["htf_bias"]["value"],
        analysis=_normalize_json_value(analysis),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_signal_events_for_assignment(
    db: AsyncSession,
    *,
    assignment_id: int,
    user_id: int,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[int, list[SignalEvent]]:
    base_stmt: Select = _apply_signal_event_filters(
        select(SignalEvent),
        assignment_id=assignment_id,
        user_id=user_id,
        created_from=created_from,
        created_to=created_to,
    )
    total_stmt = _apply_signal_event_filters(
        select(func.count()).select_from(SignalEvent),
        assignment_id=assignment_id,
        user_id=user_id,
        created_from=created_from,
        created_to=created_to,
    )
    stmt = base_stmt.order_by(SignalEvent.created_at.desc(), SignalEvent.id.desc()).offset(offset).limit(limit)
    total = (await db.execute(total_stmt)).scalar_one()
    items = (await db.execute(stmt)).scalars().all()
    return total, items


async def list_signal_events_admin(
    db: AsyncSession,
    *,
    assignment_id: int | None = None,
    user_id: int | None = None,
    symbol_id: int | None = None,
    strategy_id: int | None = None,
    signal_status: SignalStatusEnum | None = None,
    trigger: SignalTriggerEnum | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[int, list[SignalEvent]]:
    total_stmt = _apply_signal_event_filters(
        select(func.count()).select_from(SignalEvent),
        assignment_id=assignment_id,
        user_id=user_id,
        symbol_id=symbol_id,
        strategy_id=strategy_id,
        signal_status=signal_status,
        trigger=trigger,
        created_from=created_from,
        created_to=created_to,
    )
    stmt: Select = _apply_signal_event_filters(
        select(SignalEvent)
        .options(
            selectinload(SignalEvent.user),
            selectinload(SignalEvent.symbol),
            selectinload(SignalEvent.strategy),
            selectinload(SignalEvent.assignment),
            selectinload(SignalEvent.trade),
        ),
        assignment_id=assignment_id,
        user_id=user_id,
        symbol_id=symbol_id,
        strategy_id=strategy_id,
        signal_status=signal_status,
        trigger=trigger,
        created_from=created_from,
        created_to=created_to,
    )
    stmt = stmt.order_by(SignalEvent.created_at.desc(), SignalEvent.id.desc()).offset(offset).limit(limit)

    total = (await db.execute(total_stmt)).scalar_one()
    items = (await db.execute(stmt)).scalars().all()
    return total, items


def signal_event_to_dict(event: SignalEvent) -> dict:
    return {
        "id": event.id,
        "assignment_id": event.assignment_id,
        "user_id": event.user_id,
        "symbol_id": event.symbol_id,
        "strategy_id": event.strategy_id,
        "trade_id": event.trade_id,
        "trigger": event.trigger.value,
        "signal_status": event.signal_status.value,
        "signal_reason": event.signal_reason,
        "side": event.side.value if event.side is not None else None,
        "htf_bias": event.htf_bias,
        "analysis": event.analysis,
        "created_at": event.created_at,
    }


def signal_event_to_admin_dict(event: SignalEvent) -> dict:
    payload = signal_event_to_dict(event)
    payload.update(
        {
            "username": event.user.username if event.user is not None else None,
            "symbol": event.symbol.symbol if event.symbol is not None else None,
            "exchange": event.symbol.exchange if event.symbol is not None else None,
            "strategy_name": event.strategy.name.value if event.strategy is not None else None,
            "assignment_active": event.assignment.is_active if event.assignment is not None else None,
            "trade_status": event.trade.status.value if event.trade is not None else None,
        }
    )
    return payload
