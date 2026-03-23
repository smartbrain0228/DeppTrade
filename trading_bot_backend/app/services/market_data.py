from __future__ import annotations

import hashlib
import math
from functools import lru_cache

import ccxt
from binance import Client
from fastapi import HTTPException, status

from trading_bot_backend.app.config import settings
from trading_bot_backend.app.models import StrategyNameEnum
from trading_bot_backend.app.services.strategy import get_strategy_spec

TIMEFRAME_TO_BINANCE_INTERVAL = {
    "M1": Client.KLINE_INTERVAL_1MINUTE,
    "M5": Client.KLINE_INTERVAL_5MINUTE,
    "M15": Client.KLINE_INTERVAL_15MINUTE,
    "M30": Client.KLINE_INTERVAL_30MINUTE,
    "H1": Client.KLINE_INTERVAL_1HOUR,
    "H4": Client.KLINE_INTERVAL_4HOUR,
    "D1": Client.KLINE_INTERVAL_1DAY,
}

TIMEFRAME_TO_CCXT_INTERVAL = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

TIMEFRAME_TO_SECONDS = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}

READY_HTF_TEMPLATE = [
    {"open": 99.0, "high": 100.0, "low": 97.0, "close": 99.0, "volume": 1.0},
    {"open": 100.0, "high": 101.0, "low": 98.0, "close": 100.0, "volume": 1.0},
    {"open": 101.0, "high": 104.0, "low": 99.0, "close": 103.0, "volume": 1.0},
    {"open": 100.0, "high": 102.0, "low": 98.0, "close": 99.0, "volume": 1.0},
    {"open": 99.0, "high": 101.0, "low": 95.0, "close": 97.0, "volume": 1.0},
    {"open": 100.0, "high": 103.0, "low": 97.0, "close": 101.0, "volume": 1.0},
    {"open": 103.0, "high": 110.0, "low": 100.0, "close": 108.0, "volume": 1.0},
    {"open": 104.0, "high": 106.0, "low": 99.0, "close": 103.0, "volume": 1.0},
    {"open": 102.0, "high": 105.0, "low": 98.0, "close": 104.0, "volume": 1.0},
    {"open": 103.0, "high": 104.0, "low": 100.0, "close": 101.0, "volume": 1.0},
    {"open": 102.0, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 1.0},
    {"open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1.0},
]

READY_LTF_TEMPLATE = [
    {"open": 99.0, "high": 100.0, "low": 99.0, "close": 99.5, "volume": 1.0},
    {"open": 100.0, "high": 101.0, "low": 100.0, "close": 100.5, "volume": 1.0},
    {"open": 101.0, "high": 104.0, "low": 101.0, "close": 103.5, "volume": 1.0},
    {"open": 100.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1.0},
    {"open": 99.0, "high": 101.0, "low": 98.0, "close": 99.0, "volume": 1.0},
    {"open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1.0},
    {"open": 101.0, "high": 103.0, "low": 100.0, "close": 102.0, "volume": 1.0},
    {"open": 100.0, "high": 100.0, "low": 97.0, "close": 99.0, "volume": 1.0},
    {"open": 100.0, "high": 105.0, "low": 101.0, "close": 105.0, "volume": 1.0},
    {"open": 103.0, "high": 106.0, "low": 101.5, "close": 104.0, "volume": 1.0},
    {"open": 103.0, "high": 104.0, "low": 102.0, "close": 103.0, "volume": 1.0},
    {"open": 102.0, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 1.0},
    {"open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1.0},
]

_mexc_client = ccxt.mexc(
    {
        "enableRateLimit": True,
        "apiKey": settings.mexc_api_key,
        "secret": settings.mexc_api_secret,
    }
)


@lru_cache
def get_binance_client() -> Client:
    # Avoid a network ping during module import.
    return Client(ping=False)


def _normalize_exchange(exchange: str) -> str:
    return exchange.lower().strip()


def _normalize_symbol_for_ccxt(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if "/" in symbol:
        return symbol
    if symbol.endswith("USDT"):
        return f"{symbol[:-4]}/USDT"
    return f"{symbol}/USDT"


def _normalize_symbol_for_binance(symbol: str) -> str:
    return _normalize_symbol_for_ccxt(symbol).replace("/", "")


def _seed_from_parts(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _timeframe_seconds(timeframe: str) -> int:
    return TIMEFRAME_TO_SECONDS[timeframe.upper().strip()]


def _build_linear_candles(
    *,
    limit: int,
    step_seconds: int,
    start_time: int,
    start_price: float,
    end_price: float,
    seed: int,
) -> list[dict]:
    candles: list[dict] = []
    if limit <= 0:
        return candles

    for index in range(limit):
        progress = 0.0 if limit == 1 else index / (limit - 1)
        center = start_price + ((end_price - start_price) * progress)
        wave = math.sin((index + (seed % 17)) / 3.0) * max(center * 0.0035, 0.15)
        close_price = center + wave
        open_price = center - (wave * 0.4)
        high_price = max(open_price, close_price) + max(center * 0.0025, 0.1)
        low_price = min(open_price, close_price) - max(center * 0.0025, 0.1)
        candles.append(
            {
                "time": start_time + (index * step_seconds),
                "open": round(open_price, 6),
                "high": round(high_price, 6),
                "low": round(low_price, 6),
                "close": round(close_price, 6),
                "volume": round(100 + ((seed + index * 11) % 40), 6),
            }
        )
    return candles


def _scale_template(template: list[dict], *, scale: float, volume_scale: float) -> list[dict]:
    return [
        {
            "open": round(candle["open"] * scale, 6),
            "high": round(candle["high"] * scale, 6),
            "low": round(candle["low"] * scale, 6),
            "close": round(candle["close"] * scale, 6),
            "volume": round(candle["volume"] * volume_scale, 6),
        }
        for candle in template
    ]


def _template_to_candles(
    template: list[dict],
    *,
    timeframe: str,
    limit: int,
    seed: int,
) -> list[dict]:
    step_seconds = _timeframe_seconds(timeframe)
    base_price = 75 + (seed % 140)
    scale = base_price / 100.0
    volume_scale = 80 + (seed % 50)
    scaled_template = _scale_template(template, scale=scale, volume_scale=volume_scale)

    if limit <= len(scaled_template):
        subset = scaled_template[-limit:]
        start_time = 1_700_000_000 - ((limit - 1) * step_seconds)
        return [
            {
                "time": start_time + (index * step_seconds),
                **candle,
            }
            for index, candle in enumerate(subset)
        ]

    prefix_limit = limit - len(scaled_template)
    prefix = _build_linear_candles(
        limit=prefix_limit,
        step_seconds=step_seconds,
        start_time=1_700_000_000 - ((limit - 1) * step_seconds),
        start_price=scaled_template[0]["open"] * 0.94,
        end_price=scaled_template[0]["open"],
        seed=seed,
    )
    start_time = prefix[-1]["time"] + step_seconds if prefix else 1_700_000_000
    tail = [
        {
            "time": start_time + (index * step_seconds),
            **candle,
        }
        for index, candle in enumerate(scaled_template)
    ]
    return prefix + tail


def _build_mock_sma_cross_candles(*, timeframe: str, limit: int, seed: int) -> list[dict]:
    step_seconds = _timeframe_seconds(timeframe)
    base_price = 90 + (seed % 60)
    total = max(limit, 52)
    closes = [float(base_price)] * total
    closes[-2] = float(base_price - 1)
    closes[-1] = float(base_price + 30)

    candles: list[dict] = []
    start_time = 1_700_000_000 - ((total - 1) * step_seconds)
    for index, close_price in enumerate(closes):
        drift = math.sin((index + seed % 13) / 5.0) * 0.2
        open_price = close_price - 0.4 + drift
        high_price = max(open_price, close_price) + 0.8
        low_price = min(open_price, close_price) - 0.8
        candles.append(
            {
                "time": start_time + (index * step_seconds),
                "open": round(open_price, 6),
                "high": round(high_price, 6),
                "low": round(low_price, 6),
                "close": round(close_price, 6),
                "volume": round(100 + ((seed + index * 7) % 25), 6),
            }
        )
    return candles[-limit:]


def _build_mock_candles(
    *,
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int,
    is_futures: bool,
) -> list[dict]:
    seed = _seed_from_parts(
        settings.market_data_mock_seed,
        exchange.lower().strip(),
        symbol.upper().strip(),
        timeframe.upper().strip(),
        "futures" if is_futures else "spot",
    )
    step_seconds = _timeframe_seconds(timeframe)
    start_price = float(85 + (seed % 115))
    end_price = start_price * (1.03 if is_futures else 1.015)
    return _build_linear_candles(
        limit=limit,
        step_seconds=step_seconds,
        start_time=1_700_000_000 - ((limit - 1) * step_seconds),
        start_price=start_price,
        end_price=end_price,
        seed=seed,
    )


def _build_mock_strategy_candles(
    *,
    exchange: str,
    symbol: str,
    strategy_name: StrategyNameEnum,
    htf_limit: int | None,
    ltf_limit: int | None,
) -> dict:
    spec = get_strategy_spec(strategy_name)
    htf_seed = _seed_from_parts(
        settings.market_data_mock_seed,
        exchange.lower().strip(),
        symbol.upper().strip(),
        strategy_name.value,
        spec.htf,
        "htf",
    )
    ltf_seed = _seed_from_parts(
        settings.market_data_mock_seed,
        exchange.lower().strip(),
        symbol.upper().strip(),
        strategy_name.value,
        spec.ltf,
        "ltf",
    )

    if strategy_name == StrategyNameEnum.SMA_CROSS:
        return {
            "htf": _build_mock_candles(
                exchange=exchange,
                symbol=symbol,
                timeframe=spec.htf,
                limit=htf_limit or spec.htf_limit,
                is_futures=False,
            ),
            "ltf": _build_mock_sma_cross_candles(
                timeframe=spec.ltf,
                limit=ltf_limit or spec.ltf_limit,
                seed=ltf_seed,
            ),
        }

    return {
        "htf": _template_to_candles(
            READY_HTF_TEMPLATE,
            timeframe=spec.htf,
            limit=htf_limit or spec.htf_limit,
            seed=htf_seed,
        ),
        "ltf": _template_to_candles(
            READY_LTF_TEMPLATE,
            timeframe=spec.ltf,
            limit=ltf_limit or spec.ltf_limit,
            seed=ltf_seed,
        ),
    }


def fetch_candles(
    *,
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int,
    is_futures: bool = False,
) -> list[dict]:
    exchange = _normalize_exchange(exchange)
    timeframe = timeframe.upper().strip()

    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="limit must be between 1 and 1000.",
        )

    if timeframe not in TIMEFRAME_TO_BINANCE_INTERVAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported timeframe: {timeframe}.",
        )

    if settings.use_mock_market_data:
        return _build_mock_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            is_futures=is_futures,
        )

    try:
        if exchange == "binance":
            client = get_binance_client()
            symbol_str = _normalize_symbol_for_binance(symbol)
            interval = TIMEFRAME_TO_BINANCE_INTERVAL[timeframe]

            if is_futures:
                klines = client.futures_klines(
                    symbol=symbol_str,
                    interval=interval,
                    limit=limit,
                )
            else:
                klines = client.get_klines(
                    symbol=symbol_str,
                    interval=interval,
                    limit=limit,
                )
            return [
                {
                    "time": int(kline[0] / 1000),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                }
                for kline in klines
            ]

        if exchange == "mexc":
            klines = _mexc_client.fetch_ohlcv(
                _normalize_symbol_for_ccxt(symbol),
                timeframe=TIMEFRAME_TO_CCXT_INTERVAL[timeframe],
                limit=limit,
            )
            return [
                {
                    "time": int(kline[0] / 1000),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                }
                for kline in klines
            ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported exchange.")


def fetch_strategy_candles(
    *,
    exchange: str,
    symbol: str,
    strategy_name: StrategyNameEnum,
    htf_limit: int | None = None,
    ltf_limit: int | None = None,
) -> dict:
    if settings.use_mock_market_data:
        return _build_mock_strategy_candles(
            exchange=exchange,
            symbol=symbol,
            strategy_name=strategy_name,
            htf_limit=htf_limit,
            ltf_limit=ltf_limit,
        )

    spec = get_strategy_spec(strategy_name)
    return {
        "htf": fetch_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=spec.htf,
            limit=htf_limit or spec.htf_limit,
        ),
        "ltf": fetch_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=spec.ltf,
            limit=ltf_limit or spec.ltf_limit,
        ),
    }
