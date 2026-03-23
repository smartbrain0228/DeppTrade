from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from trading_bot_backend.app.models import StrategyNameEnum
from trading_bot_backend.app.services.backtest import BacktestEngine
from trading_bot_backend.app.services.market_data import fetch_candles

router = APIRouter(prefix="/backtest", tags=["backtest"])

class BacktestRequest(BaseModel):
    strategy_name: StrategyNameEnum
    exchange: str = "binance"
    symbol: str = "BTC/USDT"
    initial_balance: float = 10000.0
    risk_pct: float = 0.01
    htf_limit: int = 500
    ltf_limit: int = 1000

@router.post("")
async def run_backtest(req: BacktestRequest):
    try:
        # 1. Fetch historical data
        # For a real backtest, we might need much more than 1000 candles
        # but for this demo, we use the available limit.
        htf_candles = fetch_candles(
            exchange=req.exchange,
            symbol=req.symbol,
            timeframe="H4", # Standard HTF for SMC
            limit=req.htf_limit
        )
        
        ltf_candles = fetch_candles(
            exchange=req.exchange,
            symbol=req.symbol,
            timeframe="M15", # Standard LTF for SMC
            limit=req.ltf_limit
        )

        # 2. Run engine
        engine = BacktestEngine(
            strategy_name=req.strategy_name,
            initial_balance=req.initial_balance,
            risk_pct=req.risk_pct
        )
        
        result = engine.run(htf_candles, ltf_candles)
        
        return {
            "total_trades": result.total_trades,
            "wins": result.wins,
            "losses": result.losses,
            "win_rate": result.win_rate,
            "total_profit": result.total_profit,
            "profit_factor": result.profit_factor,
            "max_drawdown": result.max_drawdown,
            "trades": [
                {
                    "side": t.side.value,
                    "entry": t.entry_price,
                    "sl": t.stop_loss,
                    "tp": t.take_profit,
                    "pnl": t.pnl,
                    "opened_at": t.opened_at,
                    "closed_at": t.closed_at
                } for t in engine.closed_trades
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
