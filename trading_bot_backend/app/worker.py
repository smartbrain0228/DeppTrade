import asyncio
import logging
from decimal import Decimal
from datetime import datetime, time

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.db import AsyncSessionLocal
from trading_bot_backend.app.models import Trade, TradeStatusEnum, User, UserPairStrategy
from trading_bot_backend.app.services.market_data import fetch_candles
from trading_bot_backend.app.services.trade_management import apply_trade_management
from trading_bot_backend.app.services.notifications import send_telegram_message
from trading_bot_backend.app.services.telegram_templates import get_daily_summary_template

logger = logging.getLogger(__name__)

async def monitor_trades_loop():
    """
    Background loop to monitor open trades and apply trade management logic.
    Also handles daily summary at midnight.
    """
    logger.info("Starting trade monitoring loop...")
    last_summary_date = None

    while True:
        try:
            now = datetime.now()
            
            # --- Daily Summary Logic ---
            # Check if it's past midnight and we haven't sent today's summary
            current_date = now.date()
            if last_summary_date is None or current_date > last_summary_date:
                # We send summary for the PREVIOUS day if it's just after midnight, 
                # or just start tracking from now if first run.
                if last_summary_date is not None:
                    await send_daily_summary(last_summary_date)
                last_summary_date = current_date

            async with AsyncSessionLocal() as db:
                # 1. Fetch all OPEN trades
                stmt = select(Trade).options(
                    selectinload(Trade.symbol),
                    selectinload(Trade.strategy)
                ).where(Trade.status == TradeStatusEnum.OPEN)
                result = await db.execute(stmt)
                active_trades = result.scalars().all()

                if not active_trades:
                    await asyncio.sleep(10) # Wait longer if no active trades
                    continue

                for trade in active_trades:
                    # 2. Fetch recent candles for the trade's symbol and timeframe
                    # We use the LTF for trade management as per spec (M15)
                    try:
                        candles = fetch_candles(
                            exchange=trade.symbol.exchange,
                            symbol=trade.symbol.symbol,
                            timeframe=trade.strategy.ltf,
                            limit=100 # Last 100 candles should be enough for pivots
                        )
                        
                        # 3. Apply trade management logic
                        if await apply_trade_management(db, trade, candles):
                            logger.info(f"Updated trade {trade.id} management: SL={trade.stop_loss}")
                    except Exception as e:
                        logger.error(f"Error managing trade {trade.id}: {e}")

            await asyncio.sleep(30) # Run every 30 seconds
        except Exception as e:
            logger.error(f"Error in monitor_trades_loop: {e}")
            await asyncio.sleep(60)

async def send_daily_summary(target_date):
    """
    Calculates and sends a Telegram summary for a specific date.
    """
    try:
        async with AsyncSessionLocal() as db:
            # 1. Get all closed demo trades for that day
            start_of_day = datetime.combine(target_date, time.min)
            end_of_day = datetime.combine(target_date, time.max)
            
            stmt = select(Trade).where(
                and_(
                    Trade.is_demo == True,
                    Trade.status == TradeStatusEnum.CLOSED,
                    Trade.closed_at >= start_of_day,
                    Trade.closed_at <= end_of_day
                )
            )
            result = await db.execute(stmt)
            trades = result.scalars().all()
            
            if not trades:
                logger.info(f"No trades closed on {target_date}. Skipping summary.")
                return

            # 2. Get current total demo balance for the admin user's assignments
            user_stmt = select(User).where(User.username == 'admin')
            admin = (await db.execute(user_stmt)).scalar_one_or_none()
            balance = Decimal("0")
            if admin is not None:
                balance_stmt = select(func.coalesce(func.sum(UserPairStrategy.demo_balance), 0)).where(
                    UserPairStrategy.user_id == admin.id
                )
                balance_value = (await db.execute(balance_stmt)).scalar_one()
                balance = balance_value if isinstance(balance_value, Decimal) else Decimal(str(balance_value))
            
            # 3. Calculate Stats
            total_trades = len(trades)
            wins = len([t for t in trades if (t.pnl or 0) > 0])
            losses = len([t for t in trades if (t.pnl or 0) <= 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            profit_today = sum(t.pnl or 0 for t in trades)
            
            # 4. Format and Send Message
            msg = get_daily_summary_template(
                date_str=str(target_date),
                total_trades=total_trades,
                wins=wins,
                losses=losses,
                win_rate=win_rate,
                profit_today=float(profit_today),
                balance=float(balance)
            )
            await send_telegram_message(msg)
            
    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")

def start_worker():
    asyncio.create_task(monitor_trades_loop())
