from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from trading_bot_backend.app.db import get_db
from trading_bot_backend.app.services import market_data

router = APIRouter()


@router.get("/candles")
def get_candles(
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int,
    db: Session = Depends(get_db),
):
    return market_data.fetch_candles(
        exchange=exchange, symbol=symbol, timeframe=timeframe, limit=limit
    )
