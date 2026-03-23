from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.db import get_db
from sqlalchemy import select, func, and_
from trading_bot_backend.app.models import (
    Trade,
    TradeSideEnum,
    TradeStatusEnum,
    User,
    UserPairStrategy,
)
from trading_bot_backend.app.services.trade_execution import (
    create_trade as create_trade_service,
    get_trade_for_user,
    list_user_trades,
    trade_to_dict,
    update_trade as update_trade_service,
)
from trading_bot_backend.app.users.deps import get_current_user

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("/restart/{assignment_id}")
async def restart_strategy(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserPairStrategy).where(
        and_(
            UserPairStrategy.id == assignment_id,
            UserPairStrategy.user_id == current_user.id
        )
    )
    assignment = (await db.execute(stmt)).scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Reset trade count and pause state
    assignment.trade_count = 0
    assignment.is_paused = False
    # Keep historical trades but reset the current cycle
    await db.commit()
    
    return {"message": f"Strategy {assignment.id} restarted successfully"}


class TradeStats(BaseModel):
    bot_status: str
    current_balance: float
    initial_balance: float = 100.0
    total_trades: int
    skipped: int = 0
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    recent_trades: list[dict] = []
    open_trades: list[dict] = []
    # Multi-strategy extensions
    strategy_id: int | None = None
    strategy_name: str | None = None
    trade_count: int = 0
    is_paused: bool = False


@router.get("/multi-stats", response_model=list[TradeStats])
async def get_multi_trade_stats(
    interval: str = Query("all", pattern="^(1h|6h|24h|7d|all)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch all assignments
    stmt = select(UserPairStrategy).options(
        selectinload(UserPairStrategy.strategy)
    ).where(UserPairStrategy.user_id == current_user.id)
    assignments = (await db.execute(stmt)).scalars().all()
    
    results = []
    for assignment in assignments:
        # 2. Terminal trades for THIS strategy
        terminal_stmt = select(Trade).options(
            selectinload(Trade.symbol)
        ).where(
            and_(
                Trade.user_id == current_user.id,
                Trade.strategy_id == assignment.strategy_id,
                Trade.is_demo == True,
                Trade.status.in_(
                    (TradeStatusEnum.CLOSED, TradeStatusEnum.SKIPPED, TradeStatusEnum.CANCELED)
                ),
            )
        )

        # 3. Query for OPEN trades for THIS strategy
        open_stmt = select(Trade).options(
            selectinload(Trade.symbol)
        ).where(
            and_(
                Trade.user_id == current_user.id,
                Trade.strategy_id == assignment.strategy_id,
                Trade.is_demo == True,
                Trade.status == TradeStatusEnum.OPEN
            )
        )

        # 4. Apply time filter
        if interval != "all":
            now = datetime.now()
            delta = timedelta(hours=1) if interval == "1h" else \
                    timedelta(hours=6) if interval == "6h" else \
                    timedelta(days=1) if interval == "24h" else \
                    timedelta(days=7)
            threshold = now - delta
            terminal_stmt = terminal_stmt.where(
                func.coalesce(Trade.closed_at, Trade.opened_at) >= threshold
            )

        terminal_stmt = terminal_stmt.order_by(
            func.coalesce(Trade.closed_at, Trade.opened_at).desc()
        )
        
        terminal_trades = (await db.execute(terminal_stmt)).scalars().all()
        open_trades = (await db.execute(open_stmt)).scalars().all()

        closed_trades = [t for t in terminal_trades if t.status == TradeStatusEnum.CLOSED]
        skipped_trades = [t for t in terminal_trades if t.status == TradeStatusEnum.SKIPPED]
        wins = len([t for t in closed_trades if (t.pnl or 0) > 0])
        losses = len([t for t in closed_trades if (t.pnl or 0) <= 0])
        skipped = len(skipped_trades)
        total_trades = len(closed_trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = float(sum(t.pnl or 0 for t in closed_trades))

        results.append(TradeStats(
            bot_status="RUNNING",
            current_balance=float(assignment.demo_balance),
            initial_balance=100.0,
            total_trades=total_trades,
            skipped=skipped,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_pnl=total_pnl,
            strategy_id=assignment.id,
            strategy_name=assignment.strategy.name,
            trade_count=assignment.trade_count,
            is_paused=assignment.is_paused,
            recent_trades=[{
                "id": t.id,
                "pair": t.symbol.symbol if t.symbol else "N/A",
                "side": t.side.value,
                "entry": float(t.entry_price),
                "exit": float(t.exit_price) if t.exit_price else 0,
                "pnl": float(t.pnl) if t.pnl else 0,
                "status": t.status.value,
                "result": (
                    "SKIPPED"
                    if t.status == TradeStatusEnum.SKIPPED
                    else "WIN"
                    if (t.pnl or 0) > 0
                    else "FAIL"
                ),
                "timestamp": (t.closed_at or t.opened_at).isoformat() if (t.closed_at or t.opened_at) else None
            } for t in terminal_trades[:6]],
            open_trades=[{
                "id": t.id,
                "pair": t.symbol.symbol if t.symbol else "N/A",
                "side": t.side.value,
                "entry": float(t.entry_price),
                "sl": float(t.stop_loss),
                "tp": float(t.take_profit)
            } for t in open_trades]
        ))
    
    return results


class TradeCreate(BaseModel):
    symbol_id: int
    strategy_id: int
    side: TradeSideEnum
    entry_price: Decimal = Field(gt=Decimal("0"))
    stop_loss: Decimal = Field(gt=Decimal("0"))
    take_profit: Decimal = Field(gt=Decimal("0"))
    quantity: Decimal = Field(gt=Decimal("0"))
    status: TradeStatusEnum = TradeStatusEnum.PENDING


class TradeUpdate(BaseModel):
    status: TradeStatusEnum | None = None
    stop_loss: Decimal | None = Field(default=None, gt=Decimal("0"))
    take_profit: Decimal | None = Field(default=None, gt=Decimal("0"))
    pnl: Decimal | None = None
    closed_at: datetime | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trade(
    payload: TradeCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trade = await create_trade_service(
        db,
        user=current_user,
        symbol_id=payload.symbol_id,
        strategy_id=payload.strategy_id,
        side=payload.side,
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        quantity=payload.quantity,
        trade_status=payload.status,
    )
    return trade_to_dict(trade)


@router.get("")
async def list_my_trades(
    status_filter: TradeStatusEnum | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trades = await list_user_trades(
        db,
        user_id=current_user.id,
        status_filter=status_filter,
        limit=limit,
    )
    return [trade_to_dict(trade) for trade in trades]


@router.get("/{trade_id}")
async def get_trade(
    trade_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trade = await get_trade_for_user(db, trade_id, current_user.id)
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found.")
    return trade_to_dict(trade)


@router.patch("/{trade_id}")
async def update_trade(
    trade_id: int,
    payload: TradeUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trade = await get_trade_for_user(db, trade_id, current_user.id)
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found.")

    updated = await update_trade_service(
        db,
        trade=trade,
        status_value=payload.status,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        pnl=payload.pnl,
        closed_at=payload.closed_at,
    )
    return trade_to_dict(updated)
