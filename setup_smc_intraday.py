import asyncio
from trading_bot_backend.app.db import AsyncSessionLocal
from trading_bot_backend.app.models import User, Strategy, Symbol, UserPairStrategy, StrategyNameEnum
from sqlalchemy import select, delete

async def setup_smc_intraday():
    async with AsyncSessionLocal() as db:
        # 1. Get or create admin user
        result = await db.execute(select(User).where(User.username == 'admin'))
        admin = result.scalar_one_or_none()
        if not admin:
            print("Admin user not found. Please create it first.")
            return

        # 2. Get or create SMC_INTRADAY strategy
        result = await db.execute(select(Strategy).where(Strategy.name == StrategyNameEnum.SMC_INTRADAY))
        smc_strategy = result.scalar_one_or_none()
        if not smc_strategy:
            smc_strategy = Strategy(name=StrategyNameEnum.SMC_INTRADAY, htf="H4", ltf="M15", is_active=True)
            db.add(smc_strategy)
            await db.commit()
            await db.refresh(smc_strategy)
            print(f"Created strategy: {smc_strategy.name}")
        else:
            # Update timeframes to match user spec exactly
            smc_strategy.htf = "H4"
            smc_strategy.ltf = "M15"
            await db.commit()
            print(f"Strategy {smc_strategy.name} updated to H4/M15.")

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

        # 4. Assign SMC_INTRADAY to admin for BTC/USDT
        # First, remove any existing assignment for this user and symbol to avoid unique constraint violation
        await db.execute(delete(UserPairStrategy).where(
            UserPairStrategy.user_id == admin.id,
            UserPairStrategy.symbol_id == btc_symbol.id
        ))
        await db.commit()

        assignment = UserPairStrategy(
            user_id=admin.id,
            symbol_id=btc_symbol.id,
            strategy_id=smc_strategy.id,
            risk_pct=1.0, # User spec: 1%
            max_trades_per_day=3,
            is_active=True
        )
        db.add(assignment)
        await db.commit()
        print(f"Assigned {smc_strategy.name} to {admin.username} for {btc_symbol.symbol}")

if __name__ == "__main__":
    asyncio.run(setup_smc_intraday())
