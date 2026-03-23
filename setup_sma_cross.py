import asyncio
from trading_bot_backend.app.db import AsyncSessionLocal
from trading_bot_backend.app.models import User, Strategy, Symbol, UserPairStrategy, StrategyNameEnum
from sqlalchemy import select

async def setup_sma_cross():
    async with AsyncSessionLocal() as db:
        # 1. Get or create admin user
        result = await db.execute(select(User).where(User.username == 'admin'))
        admin = result.scalar_one_or_none()
        if not admin:
            print("Admin user not found. Please create it first.")
            return

        # 2. Get or create SMA_CROSS strategy
        result = await db.execute(select(Strategy).where(Strategy.name == StrategyNameEnum.SMA_CROSS))
        sma_strategy = result.scalar_one_or_none()
        if not sma_strategy:
            sma_strategy = Strategy(name=StrategyNameEnum.SMA_CROSS, htf="D1", ltf="H1", is_active=True)
            db.add(sma_strategy)
            await db.commit()
            await db.refresh(sma_strategy)
            print(f"Created strategy: {sma_strategy.name}")
        else:
            print(f"Strategy {sma_strategy.name} already exists.")

        # 3. Get or create BTC/USDT symbol
        result = await db.execute(select(Symbol).where(Symbol.symbol == 'BTC/USDT', Symbol.exchange == 'binance'))
        btc_symbol = result.scalar_one_or_none()
        if not btc_symbol:
            btc_symbol = Symbol(exchange='binance', symbol='BTC/USDT', base_asset='BTC', quote_asset='USDT', is_active=True)
            db.add(btc_symbol)
            await db.commit()
            await db.refresh(btc_symbol)
            print(f"Created symbol: {btc_symbol.symbol}")
        else:
            print(f"Symbol {btc_symbol.symbol} already exists.")

        # 4. Assign SMA_CROSS to admin for BTC/USDT
        result = await db.execute(select(UserPairStrategy).where(
            UserPairStrategy.user_id == admin.id,
            UserPairStrategy.symbol_id == btc_symbol.id,
            UserPairStrategy.strategy_id == sma_strategy.id
        ))
        assignment = result.scalar_one_or_none()
        if not assignment:
            assignment = UserPairStrategy(
                user_id=admin.id,
                symbol_id=btc_symbol.id,
                strategy_id=sma_strategy.id,
                risk_pct=1.0,
                max_trades_per_day=3,
                is_active=True
            )
            db.add(assignment)
            await db.commit()
            print(f"Assigned {sma_strategy.name} to {admin.username} for {btc_symbol.symbol}")
        else:
            print("Assignment already exists.")

if __name__ == "__main__":
    asyncio.run(setup_sma_cross())
