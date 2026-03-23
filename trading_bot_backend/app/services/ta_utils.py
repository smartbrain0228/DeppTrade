from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: Literal["high", "low"]
    time: int

def find_pivots(candles: list[Candle], pivot_window: int) -> tuple[list[Pivot], list[Pivot]]:
    highs: list[Pivot] = []
    lows: list[Pivot] = []
    for index in range(pivot_window, len(candles) - pivot_window):
        candle = candles[index]
        left = candles[index - pivot_window : index]
        right = candles[index + 1 : index + pivot_window + 1]

        if all(candle.high > item.high for item in left + right):
            highs.append(Pivot(index=index, price=candle.high, kind="high", time=candle.time))
        if all(candle.low < item.low for item in left + right):
            lows.append(Pivot(index=index, price=candle.low, kind="low", time=candle.time))
    return highs, lows
