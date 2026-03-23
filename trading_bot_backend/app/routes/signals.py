from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from fastapi import Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from trading_bot_backend.app.db import get_db
from trading_bot_backend.app.models import StrategyNameEnum
from trading_bot_backend.app.models import TradeStatusEnum
from trading_bot_backend.app.services.signal_execution import (
    analyze_assignment_signal,
    execute_assignment_signal,
    get_assignment_for_user,
)
from trading_bot_backend.app.services.signal_history import (
    list_signal_events_for_assignment,
    signal_event_to_dict,
)
from trading_bot_backend.app.services.signal_overlays import build_assignment_overlay_payload
from trading_bot_backend.app.services.strategy import analyze_strategy
from trading_bot_backend.app.users.deps import get_current_user

router = APIRouter(prefix="/signals", tags=["signals"])


class CandleInput(BaseModel):
    time: int = Field(..., description="Unix timestamp in seconds")
    open: float
    high: float
    low: float
    close: float
    volume: float


class StrategyPreviewRequest(BaseModel):
    strategy: StrategyNameEnum
    htf_candles: list[CandleInput]
    ltf_candles: list[CandleInput]


class AssignmentSignalScanRequest(BaseModel):
    htf_limit: int | None = Field(default=None, ge=5, le=1000)
    ltf_limit: int | None = Field(default=None, ge=5, le=1000)


class AssignmentSignalExecuteRequest(BaseModel):
    quantity: Decimal = Field(gt=Decimal("0"))
    status: TradeStatusEnum = TradeStatusEnum.PENDING
    htf_limit: int | None = Field(default=None, ge=5, le=1000)
    ltf_limit: int | None = Field(default=None, ge=5, le=1000)


@router.post("/preview")
async def preview_strategy(payload: StrategyPreviewRequest):
    try:
        return analyze_strategy(
            strategy_name=payload.strategy,
            htf_candles=[candle.model_dump() for candle in payload.htf_candles],
            ltf_candles=[candle.model_dump() for candle in payload.ltf_candles],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/assignments/{assignment_id}/scan")
async def scan_assignment_signal(
    assignment_id: int,
    payload: AssignmentSignalScanRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await analyze_assignment_signal(
            db,
            user=current_user,
            assignment_id=assignment_id,
            htf_limit=payload.htf_limit,
            ltf_limit=payload.ltf_limit,
            persist=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/assignments/{assignment_id}/execute", status_code=status.HTTP_201_CREATED)
async def execute_assignment_trade(
    assignment_id: int,
    payload: AssignmentSignalExecuteRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await execute_assignment_signal(
            db,
            user=current_user,
            assignment_id=assignment_id,
            quantity=payload.quantity,
            trade_status=payload.status,
            htf_limit=payload.htf_limit,
            ltf_limit=payload.ltf_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/assignments/{assignment_id}/history")
async def get_assignment_signal_history(
    assignment_id: int,
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_assignment_for_user(db, assignment_id=assignment_id, user_id=current_user.id)
    total, events = await list_signal_events_for_assignment(
        db,
        assignment_id=assignment_id,
        user_id=current_user.id,
        created_from=created_from,
        created_to=created_to,
        offset=offset,
        limit=limit,
    )
    return {
        "assignment_id": assignment_id,
        "total": total,
        "count": len(events),
        "offset": offset,
        "limit": limit,
        "filters": {
            "created_from": created_from,
            "created_to": created_to,
        },
        "items": [signal_event_to_dict(event) for event in events],
    }


@router.get("/assignments/{assignment_id}/overlay")
async def get_assignment_signal_overlay(
    assignment_id: int,
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_assignment_for_user(db, assignment_id=assignment_id, user_id=current_user.id)
    total, events = await list_signal_events_for_assignment(
        db,
        assignment_id=assignment_id,
        user_id=current_user.id,
        created_from=created_from,
        created_to=created_to,
        offset=offset,
        limit=limit,
    )
    return build_assignment_overlay_payload(
        assignment_id=assignment_id,
        total=total,
        offset=offset,
        limit=limit,
        events=events,
    )
