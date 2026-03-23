from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from trading_bot_backend.app.models import (
    StrategyNameEnum,
    Trade,
    TradeSideEnum,
    TradeStatusEnum,
    UserPairStrategy,
)
from trading_bot_backend.app.services.ta_utils import Candle, find_pivots
from trading_bot_backend.app.services.notifications import send_telegram_message
from trading_bot_backend.app.services.telegram_templates import get_trade_closed_template

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

async def apply_trade_management(
    db: AsyncSession,
    trade: Trade,
    current_candles: list[dict],
) -> bool:
    """
    Applies break-even, trailing stop and trade exit logic (TP/SL).
    Returns True if the trade was updated or closed.
    """
    if not current_candles:
        return False
    
    candles = [Candle(**c) for c in current_candles]
    last_candle = candles[-1]
    current_price = Decimal(str(last_candle.close))
    high_price = Decimal(str(last_candle.high))
    low_price = Decimal(str(last_candle.low))
    
    entry_price = trade.entry_price
    sl_price = trade.stop_loss
    tp_price = trade.take_profit
    side = trade.side
    
    # --- 0. Check for TP/SL (Exit Logic) ---
    closed = False
    if side == TradeSideEnum.BUY:
        if low_price <= sl_price:
            trade.exit_price = sl_price
            trade.status = TradeStatusEnum.CLOSED
            closed = True
        elif high_price >= tp_price:
            trade.exit_price = tp_price
            trade.status = TradeStatusEnum.CLOSED
            closed = True
    elif side == TradeSideEnum.SELL:
        if high_price >= sl_price:
            trade.exit_price = sl_price
            trade.status = TradeStatusEnum.CLOSED
            closed = True
        elif low_price <= tp_price:
            trade.exit_price = tp_price
            trade.status = TradeStatusEnum.CLOSED
            closed = True
            
    if closed:
        trade.closed_at = datetime.now(timezone.utc)
        # Calculate PnL
        if side == TradeSideEnum.BUY:
            trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        else:
            trade.pnl = (trade.entry_price - trade.exit_price) * trade.quantity

        assignment_balance = Decimal("0")
        if trade.is_demo and trade.user_id is not None:
            assignment_stmt = select(UserPairStrategy).where(
                UserPairStrategy.user_id == trade.user_id,
                UserPairStrategy.symbol_id == trade.symbol_id,
                UserPairStrategy.strategy_id == trade.strategy_id,
            )
            assignment = (await db.execute(assignment_stmt)).scalar_one_or_none()
            if assignment is not None:
                assignment.demo_balance += trade.pnl
                assignment_balance = assignment.demo_balance

        # --- Telegram Notification ---
        msg = get_trade_closed_template(
            symbol=trade.symbol.symbol if trade.symbol else "N/A",
            side=trade.side.value,
            entry_price=float(trade.entry_price),
            exit_price=float(trade.exit_price),
            pnl=float(trade.pnl),
            balance=float(assignment_balance),
            is_tp=trade.pnl > 0,
            strategy_name=trade.strategy.name if trade.strategy else None,
            mode="Demo" if trade.is_demo else "Live",
            closed_at=trade.closed_at,
        )
        await send_telegram_message(msg)
            
        await db.commit()
        return True

    # --- 1. Strategy Specific Management (SMC) ---
    if trade.tag not in [StrategyNameEnum.SMC_INTRADAY, StrategyNameEnum.SMC_H4_M15, StrategyNameEnum.SMC_H1_M5]:
        return False

    # 1. Break-even rule
    # reaches 1R (profit equal to initial risk)
    # risk = abs(entry_price - sl_price) if not trade.is_be_reached else Decimal("0")
    # For multi-strategy, we use the 1R rule strictly.
    risk = abs(entry_price - sl_price) if not trade.is_be_reached else Decimal("0")
    updated = False

    # Volatility for dynamic trailing speed
    vol = _calculate_volatility(candles)
    # Rule: Fast market -> move SL quickly. Calm market -> move slowly.
    # In our implementation, we'll just check if we should update every cycle.
    # A "slow" trailing might mean we only update if the new pivot is significantly better.
    
    if not trade.is_be_reached:
        if side == TradeSideEnum.BUY:
            if current_price >= entry_price + risk:
                trade.stop_loss = entry_price
                trade.is_be_reached = True
                updated = True
        elif side == TradeSideEnum.SELL:
            if current_price <= entry_price - risk:
                trade.stop_loss = entry_price
                trade.is_be_reached = True
                updated = True

    # 2. Trailing Stop based on market structure (after BE)
    if trade.is_be_reached:
        # SMC Trailing: move SL below new Higher Low (BUY) or above new Lower High (SELL)
        highs, lows = find_pivots(candles, pivot_window=2)
        
        if side == TradeSideEnum.BUY:
            # Rule: move SL below each new Higher Low
            valid_lows = [Decimal(str(p.price)) for p in lows if Decimal(str(p.price)) > trade.stop_loss]
            if valid_lows:
                new_sl = valid_lows[-1]
                # Dynamic speed: in calm market (vol < 0.8), only move if gap is > 0.5%
                move_threshold = Decimal("0.005") if vol < 0.8 else Decimal("0")
                if new_sl > trade.stop_loss + (trade.stop_loss * move_threshold):
                    trade.stop_loss = new_sl
                    trade.last_swing_sl = new_sl
                    updated = True
        
        elif side == TradeSideEnum.SELL:
            valid_highs = [Decimal(str(p.price)) for p in highs if Decimal(str(p.price)) < trade.stop_loss]
            if valid_highs:
                new_sl = valid_highs[-1]
                move_threshold = Decimal("0.005") if vol < 0.8 else Decimal("0")
                if new_sl < trade.stop_loss - (trade.stop_loss * move_threshold):
                    trade.stop_loss = new_sl
                    trade.last_swing_sl = new_sl
                    updated = True

    if updated:
        await db.commit()
        return True
    
    return False


def _calculate_volatility(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period:
        return 1.0
    ranges = [c.high - c.low for c in candles[-period:]]
    avg_range = sum(ranges) / period
    current_range = candles[-1].high - candles[-1].low
    if avg_range == 0:
        return 1.0
    return current_range / avg_range
