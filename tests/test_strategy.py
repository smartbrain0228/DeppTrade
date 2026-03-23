from trading_bot_backend.app.models import StrategyNameEnum
from trading_bot_backend.app.services.strategy import analyze_strategy


def test_analyze_strategy_builds_ready_bullish_signal():
    htf_candles = [
        {"time": 1, "open": 99, "high": 100, "low": 97, "close": 99, "volume": 1},
        {"time": 2, "open": 100, "high": 101, "low": 98, "close": 100, "volume": 1},
        {"time": 3, "open": 101, "high": 104, "low": 99, "close": 103, "volume": 1},
        {"time": 4, "open": 100, "high": 102, "low": 98, "close": 99, "volume": 1},
        {"time": 5, "open": 99, "high": 101, "low": 95, "close": 97, "volume": 1},
        {"time": 6, "open": 100, "high": 103, "low": 97, "close": 101, "volume": 1},
        {"time": 7, "open": 103, "high": 110, "low": 100, "close": 108, "volume": 1},
        {"time": 8, "open": 104, "high": 106, "low": 99, "close": 103, "volume": 1},
        {"time": 9, "open": 102, "high": 105, "low": 98, "close": 104, "volume": 1},
        {"time": 10, "open": 103, "high": 104, "low": 100, "close": 101, "volume": 1},
        {"time": 11, "open": 102, "high": 103, "low": 101, "close": 102, "volume": 1},
        {"time": 12, "open": 101, "high": 102, "low": 100, "close": 101, "volume": 1},
    ]
    ltf_candles = [
        {"time": 1, "open": 99.0, "high": 100.0, "low": 99.0, "close": 99.5, "volume": 1},
        {"time": 2, "open": 100.0, "high": 101.0, "low": 100.0, "close": 100.5, "volume": 1},
        {"time": 3, "open": 101.0, "high": 104.0, "low": 101.0, "close": 103.5, "volume": 1},
        {"time": 4, "open": 100.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1},
        {"time": 5, "open": 99.0, "high": 101.0, "low": 98.0, "close": 99.0, "volume": 1},
        {"time": 6, "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1},
        {"time": 7, "open": 101.0, "high": 103.0, "low": 100.0, "close": 102.0, "volume": 1},
        {"time": 8, "open": 100.0, "high": 100.0, "low": 97.0, "close": 99.0, "volume": 1},
        {"time": 9, "open": 100.0, "high": 105.0, "low": 101.0, "close": 105.0, "volume": 1},
        {"time": 10, "open": 103.0, "high": 106.0, "low": 101.5, "close": 104.0, "volume": 1},
        {"time": 11, "open": 103.0, "high": 104.0, "low": 102.0, "close": 103.0, "volume": 1},
        {"time": 12, "open": 102.0, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 1},
        {"time": 13, "open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1},
    ]

    result = analyze_strategy(
        strategy_name=StrategyNameEnum.INTRADAY,
        htf_candles=htf_candles,
        ltf_candles=ltf_candles,
    )

    assert result["htf_bias"]["value"] == "bullish"
    assert result["signal"]["status"] == "READY"
    assert result["signal"]["side"] == "BUY"
    assert result["ltf_events"]["sweep"] is not None
    assert result["ltf_events"]["mss"] is not None
    assert result["ltf_events"]["fvg"] is not None
    assert result["signal"]["trade_plan"]["entry_price"] == 100.75
    assert result["signal"]["trade_plan"]["stop_loss"] == 97.0
    assert result["signal"]["trade_plan"]["take_profit"] == 110


def test_analyze_strategy_returns_no_bias_when_htf_is_mixed():
    flat_htf = [
        {"time": 1, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": 2, "open": 101, "high": 102, "low": 100, "close": 101, "volume": 1},
        {"time": 3, "open": 102, "high": 105, "low": 101, "close": 104, "volume": 1},
        {"time": 4, "open": 101, "high": 103, "low": 100, "close": 102, "volume": 1},
        {"time": 5, "open": 100, "high": 102, "low": 96, "close": 97, "volume": 1},
        {"time": 6, "open": 101, "high": 103, "low": 98, "close": 102, "volume": 1},
        {"time": 7, "open": 102, "high": 106, "low": 100, "close": 105, "volume": 1},
        {"time": 8, "open": 101, "high": 103, "low": 99, "close": 101, "volume": 1},
        {"time": 9, "open": 100, "high": 102, "low": 95, "close": 96, "volume": 1},
        {"time": 10, "open": 100, "high": 103, "low": 98, "close": 101, "volume": 1},
        {"time": 11, "open": 101, "high": 102, "low": 99, "close": 101, "volume": 1},
        {"time": 12, "open": 102, "high": 101, "low": 100, "close": 101, "volume": 1},
    ]
    ltf_candles = [
        {"time": idx, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1}
        for idx in range(1, 14)
    ]

    result = analyze_strategy(
        strategy_name=StrategyNameEnum.SCALP,
        htf_candles=flat_htf,
        ltf_candles=ltf_candles,
    )

    assert result["htf_bias"]["value"] == "neutral"
    assert result["signal"]["status"] == "NO_BIAS"
    assert result["signal"]["trade_plan"] is None
