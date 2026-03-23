import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from trading_bot_backend.app.db import AsyncSessionLocal
from trading_bot_backend.app.models import (
    SignalTriggerEnum,
    Trade,
    TradeSideEnum,
    TradeStatusEnum,
    UserPairStrategy,
)
from trading_bot_backend.app.services.market_data import fetch_candles
from trading_bot_backend.app.services.notifications import send_telegram_message
from trading_bot_backend.app.services.signal_history import create_signal_event
from trading_bot_backend.app.services.strategy import analyze_strategy
from trading_bot_backend.app.services.telegram_templates import (
    get_interactive_keyboard,
    get_strategy_paused_template,
    get_trade_opened_template,
    get_trade_skipped_template,
)
from trading_bot_backend.app.services.trade_execution import create_trade

logger = logging.getLogger(__name__)


def _build_assignment_payload(assignment: UserPairStrategy) -> dict:
    return {
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


async def run_demo_engine():
    """
    Automated paper trading engine.
    Scans active assignments and opens trades automatically.
    """
    logger.info("Starting Multi-Strategy Demo Trading Engine...")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                stmt = (
                    select(UserPairStrategy)
                    .options(
                        selectinload(UserPairStrategy.user),
                        selectinload(UserPairStrategy.symbol),
                        selectinload(UserPairStrategy.strategy),
                    )
                    .where(UserPairStrategy.is_active == True)
                )

                result = await db.execute(stmt)
                assignments = result.scalars().all()

                for assignment in assignments:
                    if assignment.trade_count >= 50:
                        if not assignment.is_paused:
                            assignment.is_paused = True
                            await db.commit()
                            await send_telegram_message(
                                get_strategy_paused_template(
                                    strategy_name=assignment.strategy.name,
                                    symbol=assignment.symbol.symbol,
                                    trade_count=50,
                                    mode="Demo",
                                )
                            )
                        continue

                    trade_stmt = select(Trade).where(
                        Trade.user_id == assignment.user_id,
                        Trade.symbol_id == assignment.symbol_id,
                        Trade.strategy_id == assignment.strategy_id,
                        Trade.status == TradeStatusEnum.OPEN,
                    )
                    existing_trade = (await db.execute(trade_stmt)).scalar_one_or_none()
                    if existing_trade:
                        continue

                    try:
                        spot_htf = fetch_candles(
                            exchange="binance",
                            symbol=assignment.symbol.symbol,
                            timeframe=assignment.strategy.htf,
                            limit=100,
                            is_futures=False,
                        )
                        futures_htf = fetch_candles(
                            exchange="binance",
                            symbol=assignment.symbol.symbol,
                            timeframe=assignment.strategy.htf,
                            limit=100,
                            is_futures=True,
                        )
                        futures_ltf = fetch_candles(
                            exchange="binance",
                            symbol=assignment.symbol.symbol,
                            timeframe=assignment.strategy.ltf,
                            limit=200,
                            is_futures=True,
                        )

                        analysis = analyze_strategy(
                            strategy_name=assignment.strategy.name,
                            htf_candles=spot_htf,
                            ltf_candles=futures_ltf,
                            futures_htf_candles=futures_htf,
                        )
                        analysis["assignment"] = _build_assignment_payload(assignment)

                        if analysis.get("has_divergence"):
                            await create_signal_event(
                                db,
                                analysis=analysis,
                                trigger=SignalTriggerEnum.SCAN,
                                trade=None,
                            )
                            skipped_trade = Trade(
                                user_id=assignment.user_id,
                                symbol_id=assignment.symbol_id,
                                strategy_id=assignment.strategy_id,
                                side=TradeSideEnum.BUY,
                                entry_price=Decimal("0"),
                                stop_loss=Decimal("0"),
                                take_profit=Decimal("0"),
                                quantity=Decimal("0"),
                                status=TradeStatusEnum.SKIPPED,
                                has_divergence=True,
                                skip_reason=analysis.get("skip_reason"),
                                spot_bias=analysis.get("spot_bias"),
                                futures_bias=analysis.get("futures_bias"),
                                tag=assignment.strategy.name,
                                is_demo=True,
                            )
                            db.add(skipped_trade)
                            await db.commit()

                            await send_telegram_message(
                                get_trade_skipped_template(
                                    strategy_name=assignment.strategy.name,
                                    symbol=assignment.symbol.symbol,
                                    reason=analysis.get("skip_reason") or "Divergence",
                                    mode="Demo",
                                )
                            )
                            continue

                        signal = analysis.get("signal", {})
                        if signal.get("status") == "READY" and signal.get("trade_plan"):
                            plan = signal["trade_plan"]
                            balance = assignment.demo_balance
                            risk_pct = assignment.risk_pct / Decimal("100")
                            risk_amount = balance * risk_pct
                            price_risk = abs(
                                Decimal(str(plan["entry_price"]))
                                - Decimal(str(plan["stop_loss"]))
                            )

                            if price_risk > 0:
                                quantity = risk_amount / price_risk

                                logger.info(
                                    "AUTO-TRADE: Opening trade for %s [%s] - Balance: %s USDT",
                                    assignment.symbol.symbol,
                                    assignment.strategy.name,
                                    balance,
                                )

                                trade = await create_trade(
                                    db,
                                    user=assignment.user,
                                    symbol_id=assignment.symbol_id,
                                    strategy_id=assignment.strategy_id,
                                    side=TradeSideEnum(plan["side"]),
                                    entry_price=Decimal(str(plan["entry_price"])),
                                    stop_loss=Decimal(str(plan["stop_loss"])),
                                    take_profit=Decimal(str(plan["take_profit"])),
                                    quantity=quantity,
                                    trade_status=TradeStatusEnum.OPEN,
                                )
                                trade.is_demo = True
                                trade.spot_bias = analysis.get("spot_bias")
                                trade.futures_bias = analysis.get("futures_bias")
                                trade.has_divergence = False

                                assignment.trade_count += 1
                                await db.commit()

                                await create_signal_event(
                                    db,
                                    analysis=analysis,
                                    trigger=SignalTriggerEnum.EXECUTE,
                                    trade=trade,
                                )

                                message = get_trade_opened_template(
                                    strategy_name=assignment.strategy.name,
                                    symbol=assignment.symbol.symbol,
                                    side=trade.side.value,
                                    entry_price=float(trade.entry_price),
                                    stop_loss=float(trade.stop_loss),
                                    take_profit=float(trade.take_profit),
                                    balance=float(balance),
                                    quantity=float(quantity),
                                    risk_pct=float(assignment.risk_pct),
                                    mode="Demo",
                                    opened_at=trade.opened_at,
                                )
                                keyboard = get_interactive_keyboard(trade.id)
                                await send_telegram_message(
                                    message,
                                    reply_markup=keyboard,
                                )

                    except Exception as exc:
                        logger.error(
                            "Error in demo engine for assignment %s: %s",
                            assignment.id,
                            exc,
                        )

            await asyncio.sleep(60)
        except Exception as exc:
            logger.error("Error in demo engine loop: %s", exc)
            await asyncio.sleep(60)


def start_demo_engine():
    asyncio.create_task(run_demo_engine())
