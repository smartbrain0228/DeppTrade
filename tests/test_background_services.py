from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_bot_backend.app.models import (
    Strategy,
    StrategyNameEnum,
    Symbol,
    Trade,
    TradeSideEnum,
    TradeStatusEnum,
    User,
    UserPairStrategy,
)
from trading_bot_backend.app.services import demo_engine
from trading_bot_backend.app import worker


class FakeScalarSequenceResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeAsyncSession:
    def __init__(self, results):
        self.results = list(results)
        self.commits = 0
        self.added = []

    async def execute(self, _stmt):
        if not self.results:
            raise AssertionError("Unexpected execute() call in test.")
        return FakeScalarSequenceResult(self.results.pop(0))

    async def commit(self):
        self.commits += 1

    def add(self, instance):
        self.added.append(instance)


class FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def build_assignment() -> UserPairStrategy:
    user = User(id=11, email="trader@example.com", username="trader", hashed_password="x")
    symbol = Symbol(id=3, exchange="binance", symbol="SOLUSDT", base_asset="SOL", quote_asset="USDT")
    strategy = Strategy(id=2, name=StrategyNameEnum.SMA_CROSS, htf="D1", ltf="H1", is_active=True)
    assignment = UserPairStrategy(
        id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        risk_pct=Decimal("1.00"),
        max_trades_per_day=3,
        demo_balance=Decimal("1000"),
        trade_count=0,
        is_active=True,
        is_paused=False,
    )
    assignment.user = user
    assignment.symbol = symbol
    assignment.strategy = strategy
    return assignment


def build_open_trade() -> Trade:
    trade = Trade(
        id=55,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.SMA_CROSS,
        side=TradeSideEnum.BUY,
        status=TradeStatusEnum.OPEN,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("110"),
        quantity=Decimal("1"),
        opened_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
    )
    trade.symbol = Symbol(id=3, exchange="binance", symbol="SOLUSDT", base_asset="SOL", quote_asset="USDT")
    trade.strategy = Strategy(id=2, name=StrategyNameEnum.SMA_CROSS, htf="D1", ltf="H1", is_active=True)
    return trade


@pytest.mark.asyncio
async def test_monitor_trades_loop_uses_mock_market_data(monkeypatch):
    trade = build_open_trade()
    session = FakeAsyncSession([[trade]])
    applied = []

    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: FakeSessionContext(session))
    monkeypatch.setattr(worker.fetch_candles.__globals__["settings"], "market_data_mode", "mock")

    async def fake_apply_trade_management(db, current_trade, candles):
        applied.append((db, current_trade, candles))
        return False

    async def fake_sleep(seconds):
        raise asyncio.CancelledError()

    monkeypatch.setattr(worker, "apply_trade_management", fake_apply_trade_management)
    monkeypatch.setattr(worker.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await worker.monitor_trades_loop()

    assert len(applied) == 1
    assert applied[0][0] is session
    assert applied[0][1] is trade
    assert len(applied[0][2]) == 100


@pytest.mark.asyncio
async def test_send_daily_summary_sends_telegram_message(monkeypatch):
    target_date = datetime(2026, 3, 20).date()
    trade_win = Trade(
        id=1,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.INTRADAY,
        side=TradeSideEnum.BUY,
        status=TradeStatusEnum.CLOSED,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("110"),
        quantity=Decimal("1"),
        pnl=Decimal("12.5"),
        closed_at=datetime(2026, 3, 20, 9, 0, tzinfo=timezone.utc),
    )
    trade_loss = Trade(
        id=2,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.INTRADAY,
        side=TradeSideEnum.SELL,
        status=TradeStatusEnum.CLOSED,
        entry_price=Decimal("100"),
        stop_loss=Decimal("105"),
        take_profit=Decimal("90"),
        quantity=Decimal("1"),
        pnl=Decimal("-5.0"),
        closed_at=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
    )
    admin = User(id=99, email="admin@example.com", username="admin", hashed_password="x")
    session = FakeAsyncSession([[trade_win, trade_loss], admin, Decimal("2345.67")])
    sent_messages = []

    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: FakeSessionContext(session))

    async def fake_send_telegram_message(message):
        sent_messages.append(message)

    monkeypatch.setattr(worker, "send_telegram_message", fake_send_telegram_message)

    await worker.send_daily_summary(target_date)

    assert len(sent_messages) == 1
    assert "2026-03-20" in sent_messages[0]
    assert "2" in sent_messages[0]
    assert "2345.67" in sent_messages[0]


@pytest.mark.asyncio
async def test_run_demo_engine_opens_trade_in_mock_mode(monkeypatch):
    assignment = build_assignment()
    session = FakeAsyncSession([[assignment], None])
    created = []
    persisted = []
    notifications = []
    analyses = []

    monkeypatch.setattr(demo_engine, "AsyncSessionLocal", lambda: FakeSessionContext(session))
    monkeypatch.setattr(demo_engine.fetch_candles.__globals__["settings"], "market_data_mode", "mock")

    async def fake_create_trade(*args, **kwargs):
        trade = Trade(
            id=91,
            user_id=assignment.user_id,
            symbol_id=assignment.symbol_id,
            strategy_id=assignment.strategy_id,
            tag=assignment.strategy.name,
            side=kwargs["side"],
            status=kwargs["trade_status"],
            entry_price=kwargs["entry_price"],
            stop_loss=kwargs["stop_loss"],
            take_profit=kwargs["take_profit"],
            quantity=kwargs["quantity"],
            opened_at=datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc),
        )
        created.append(trade)
        return trade

    async def fake_create_signal_event(*args, **kwargs):
        persisted.append(kwargs)

    async def fake_send_telegram_message(message, reply_markup=None):
        notifications.append((message, reply_markup))

    def fake_analyze_strategy(*, strategy_name, htf_candles, ltf_candles, futures_htf_candles=None):
        analyses.append(
            {
                "strategy_name": strategy_name,
                "htf_count": len(htf_candles),
                "ltf_count": len(ltf_candles),
                "futures_htf_count": len(futures_htf_candles or []),
            }
        )
        return {
            "spot_bias": "bullish",
            "futures_bias": "bullish",
            "has_divergence": False,
            "skip_reason": None,
            "signal": {
                "status": "READY",
                "reason": "Mock analysis ready.",
                "trade_plan": {
                    "side": "BUY",
                    "entry_price": 100.0,
                    "stop_loss": 98.0,
                    "take_profit": 105.0,
                },
            },
        }

    async def fake_sleep(seconds):
        raise asyncio.CancelledError()

    monkeypatch.setattr(demo_engine, "create_trade", fake_create_trade)
    monkeypatch.setattr(demo_engine, "create_signal_event", fake_create_signal_event)
    monkeypatch.setattr(demo_engine, "send_telegram_message", fake_send_telegram_message)
    monkeypatch.setattr(demo_engine, "analyze_strategy", fake_analyze_strategy)
    monkeypatch.setattr(demo_engine.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await demo_engine.run_demo_engine()

    assert len(analyses) == 1
    assert analyses[0]["htf_count"] == 100
    assert analyses[0]["ltf_count"] == 200
    assert analyses[0]["futures_htf_count"] == 100
    assert len(created) == 1
    assert created[0].status == TradeStatusEnum.OPEN
    assert created[0].quantity > 0
    assert assignment.trade_count == 1
    assert session.commits >= 1
    assert len(persisted) == 1
    assert persisted[0]["analysis"]["assignment"]["id"] == assignment.id
    assert persisted[0]["analysis"]["assignment"]["strategy_name"] == assignment.strategy.name.value
    assert persisted[0]["analysis"]["signal"]["status"] == "READY"
    assert len(notifications) == 1
