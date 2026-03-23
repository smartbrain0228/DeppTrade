import pytest

from trading_bot_backend.app.models import StrategyNameEnum
from trading_bot_backend.app.services import market_data
from trading_bot_backend.app.services.strategy import analyze_strategy


def test_fetch_candles_returns_mock_series_when_mock_mode_enabled(monkeypatch):
    monkeypatch.setattr(market_data.settings, "market_data_mode", "mock")

    candles = market_data.fetch_candles(
        exchange="binance",
        symbol="BTCUSDT",
        timeframe="H1",
        limit=10,
    )

    assert len(candles) == 10
    assert candles[0]["time"] < candles[-1]["time"]
    assert all(candle["high"] >= max(candle["open"], candle["close"]) for candle in candles)
    assert all(candle["low"] <= min(candle["open"], candle["close"]) for candle in candles)


def test_fetch_strategy_candles_builds_ready_analysis_in_mock_mode(monkeypatch):
    monkeypatch.setattr(market_data.settings, "market_data_mode", "mock")

    candles = market_data.fetch_strategy_candles(
        exchange="binance",
        symbol="SOLUSDT",
        strategy_name=StrategyNameEnum.INTRADAY,
    )
    result = analyze_strategy(
        strategy_name=StrategyNameEnum.INTRADAY,
        htf_candles=candles["htf"],
        ltf_candles=candles["ltf"],
    )

    assert result["htf_bias"]["value"] == "bullish"
    assert result["signal"]["status"] == "READY"
    assert result["signal"]["trade_plan"] is not None


def test_fetch_candles_uses_live_provider_when_mock_mode_is_disabled(monkeypatch):
    monkeypatch.setattr(market_data.settings, "market_data_mode", "live")

    class FakeClient:
        def get_klines(self, *, symbol, interval, limit):
            assert symbol == "BTCUSDT"
            assert limit == 2
            return [
                [1_700_000_000_000, "100", "101", "99", "100.5", "10"],
                [1_700_000_060_000, "100.5", "102", "100", "101", "11"],
            ]

    monkeypatch.setattr(market_data, "get_binance_client", lambda: FakeClient())

    candles = market_data.fetch_candles(
        exchange="binance",
        symbol="BTCUSDT",
        timeframe="M1",
        limit=2,
    )

    assert candles == [
        {"time": 1_700_000_000, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0},
        {"time": 1_700_000_060, "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 11.0},
    ]


def test_fetch_strategy_candles_builds_sma_cross_signal_in_mock_mode(monkeypatch):
    monkeypatch.setattr(market_data.settings, "market_data_mode", "mock")

    candles = market_data.fetch_strategy_candles(
        exchange="binance",
        symbol="ETHUSDT",
        strategy_name=StrategyNameEnum.SMA_CROSS,
    )
    result = analyze_strategy(
        strategy_name=StrategyNameEnum.SMA_CROSS,
        htf_candles=candles["htf"],
        ltf_candles=candles["ltf"],
    )

    assert result["signal"]["status"] == "READY"
    assert result["signal"]["side"] == "BUY"
