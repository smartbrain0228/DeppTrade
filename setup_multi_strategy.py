import asyncio
from trading_bot_backend.app.db import AsyncSessionLocal
from trading_bot_backend.app.models import User, Strategy, Symbol, UserPairStrategy, StrategyNameEnum
from sqlalchemy import select, delete
from decimal import Decimal

async def setup_multi_strategy():
    async with AsyncSessionLocal() as db:
        # 1. Get admin user
        result = await db.execute(select(User).where(User.username == 'admin'))
        admin = result.scalar_one_or_none()
        if not admin:
            print("Admin user not found.")
            return

        # 2. Get BTC/USDT symbol
        result = await db.execute(select(Symbol).where(Symbol.symbol == 'BTC/USDT', Symbol.exchange == 'binance'))
        btc_symbol = result.scalar_one_or_none()
        if not btc_symbol:
            btc_symbol = Symbol(exchange='binance', symbol='BTC/USDT', base_asset='BTC', quote_asset='USDT', is_active=True)
            db.add(btc_symbol)
            await db.commit()
            await db.refresh(btc_symbol)

        # 3. Define strategies to setup
        strategies_data = [
            {"name": StrategyNameEnum.SMC_H4_M15, "htf": "H4", "ltf": "M15"},
            {"name": StrategyNameEnum.SMC_H1_M5, "htf": "H1", "ltf": "M5"},
        ]

        # Clean existing assignments for admin to start fresh
        await db.execute(delete(UserPairStrategy).where(UserPairStrategy.user_id == admin.id))
        await db.commit()

        for data in strategies_data:
            # Create or get strategy
            result = await db.execute(select(Strategy).where(Strategy.name == data["name"]))
            strategy = result.scalar_one_or_none()
            if not strategy:
                strategy = Strategy(name=data["name"], htf=data["htf"], ltf=data["ltf"], is_active=True)
                db.add(strategy)
                await db.commit()
                await db.refresh(strategy)
            else:
                strategy.htf = data["htf"]
                strategy.ltf = data["ltf"]
                await db.commit()

            # Create assignment
            assignment = UserPairStrategy(
                user_id=admin.id,
                symbol_id=btc_symbol.id,
                strategy_id=strategy.id,
                risk_pct=Decimal("1.0"),
                demo_balance=Decimal("100.0"),
                trade_count=0,
                is_paused=False,
                is_active=True
            )
            db.add(assignment)
            print(f"Setup strategy: {data['name']} (H:{data['htf']}/L:{data['ltf']})")

        await db.commit()
        print("Multi-strategy setup completed successfully.")

if __name__ == "__main__":
    asyncio.run(setup_multi_strategy())
