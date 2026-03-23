from functools import lru_cache

from binance import Client
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/binance", tags=["binance"])


@lru_cache
def get_binance_client() -> Client:
    # Avoid a network ping during module import.
    return Client(ping=False)


@router.get("/price/{symbol}")
def get_price(symbol: str):
    """
    Retrieve the current price for a symbol pair (example: BTCUSDT).
    """
    try:
        ticker = get_binance_client().get_symbol_ticker(symbol=symbol.upper())
        return {"symbol": ticker["symbol"], "price": float(ticker["price"])}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
