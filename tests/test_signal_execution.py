from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from trading_bot_backend.app.models import (
    SignalTriggerEnum,
    Strategy,
    StrategyNameEnum,
    Symbol,
    Trade,
    TradeSideEnum,
    TradeStatusEnum,
    User,
    UserPairStrategy,
)
from trading_bot_backend.app.services import signal_execution, trade_execution


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class FakeAsyncSession:
    def __init__(self, results):
        self.results = list(results)
        self.added = []
        self.commits = 0

    async def execute(self, _stmt):
        if not self.results:
            raise AssertionError("Unexpected execute() call in test.")
        return FakeScalarResult(self.results.pop(0))

    def add(self, instance):
        self.added.append(instance)

    async def commit(self):
        self.commits += 1
        for index, item in enumerate(self.added, start=1):
            if getattr(item, "id", None) is None:
                item.id = index


@pytest.mark.asyncio
async def test_execute_assignment_signal_persists_execute_event_when_signal_not_ready(monkeypatch):
    user = User(id=11, email="trader@example.com", username="trader", hashed_password="x")
    analysis = {
        "assignment": {
            "id": 7,
            "user_id": 11,
            "symbol_id": 3,
            "strategy_id": 2,
        },
        "htf_bias": {"value": "bullish"},
        "signal": {
            "status": "WAITING_FVG",
            "reason": "Setup detected but no valid executable trade plan could be derived.",
            "side": None,
            "trade_plan": None,
        },
    }
    persisted = []

    async def fake_analyze_assignment_signal(*args, **kwargs):
        return analysis

    async def fake_create_signal_event(*args, **kwargs):
        persisted.append(kwargs)

    monkeypatch.setattr(signal_execution, "analyze_assignment_signal", fake_analyze_assignment_signal)
    monkeypatch.setattr(signal_execution, "create_signal_event", fake_create_signal_event)

    with pytest.raises(HTTPException) as exc_info:
        await signal_execution.execute_assignment_signal(
            db=object(),
            user=user,
            assignment_id=7,
            quantity=Decimal("1"),
        )

    assert exc_info.value.status_code == 409
    assert "Signal is not executable" in exc_info.value.detail
    assert len(persisted) == 1
    assert persisted[0]["analysis"] == analysis
    assert persisted[0]["trigger"] == SignalTriggerEnum.EXECUTE
    assert "trade" not in persisted[0] or persisted[0]["trade"] is None


@pytest.mark.asyncio
async def test_execute_assignment_signal_creates_trade_and_persists_execute_event(monkeypatch):
    user = User(id=11, email="trader@example.com", username="trader", hashed_password="x")
    analysis = {
        "assignment": {
            "id": 7,
            "user_id": 11,
            "symbol_id": 3,
            "strategy_id": 2,
        },
        "htf_bias": {"value": "bullish"},
        "signal": {
            "status": "READY",
            "reason": "Sweep, MSS and FVG are aligned with HTF bias.",
            "side": "BUY",
            "trade_plan": {
                "side": "BUY",
                "entry_price": 100.75,
                "stop_loss": 97.0,
                "take_profit": 110.0,
            },
        },
    }
    symbol = Symbol(id=3, exchange="binance", symbol="SOL/USDT", base_asset="SOL", quote_asset="USDT")
    strategy = Strategy(id=2, name=StrategyNameEnum.INTRADAY, htf="H4", ltf="M15")
    trade = Trade(
        id=99,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.INTRADAY,
        side=TradeSideEnum.BUY,
        status=TradeStatusEnum.PENDING,
        entry_price=Decimal("100.75"),
        stop_loss=Decimal("97.0"),
        take_profit=Decimal("110.0"),
        quantity=Decimal("1"),
        opened_at=datetime(2026, 3, 13, tzinfo=timezone.utc),
    )
    trade.symbol = symbol
    trade.strategy = strategy
    persisted = []

    async def fake_analyze_assignment_signal(*args, **kwargs):
        return analysis

    async def fake_create_trade(*args, **kwargs):
        assert kwargs["symbol_id"] == 3
        assert kwargs["strategy_id"] == 2
        assert kwargs["side"] == TradeSideEnum.BUY
        return trade

    async def fake_create_signal_event(*args, **kwargs):
        persisted.append(kwargs)

    monkeypatch.setattr(signal_execution, "analyze_assignment_signal", fake_analyze_assignment_signal)
    monkeypatch.setattr(signal_execution, "create_trade", fake_create_trade)
    monkeypatch.setattr(signal_execution, "create_signal_event", fake_create_signal_event)

    result = await signal_execution.execute_assignment_signal(
        db=object(),
        user=user,
        assignment_id=7,
        quantity=Decimal("1"),
    )

    assert result["analysis"] == analysis
    assert result["trade"]["id"] == 99
    assert result["trade"]["symbol"] == "SOL/USDT"
    assert result["trade"]["strategy_name"] == "INTRADAY"
    assert len(persisted) == 1
    assert persisted[0]["trigger"] == SignalTriggerEnum.EXECUTE
    assert persisted[0]["trade"] is trade


@pytest.mark.asyncio
async def test_create_trade_rejects_when_daily_limit_is_reached(monkeypatch):
    user = User(id=11, email="trader@example.com", username="trader", hashed_password="x")
    mapping = UserPairStrategy(
        id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        risk_pct=Decimal("1.00"),
        max_trades_per_day=1,
        is_active=True,
    )
    strategy = Strategy(id=2, name=StrategyNameEnum.INTRADAY, htf="H4", ltf="M15", is_active=True)
    symbol = Symbol(id=3, exchange="binance", symbol="SOL/USDT", base_asset="SOL", quote_asset="USDT", is_active=True)
    db = FakeAsyncSession([mapping, strategy, symbol])

    async def fake_get_daily_trade_count(*args, **kwargs):
        return 1

    async def fake_get_active_risk_pct(*args, **kwargs):
        return Decimal("0.00")

    monkeypatch.setattr(trade_execution, "get_daily_trade_count", fake_get_daily_trade_count)
    monkeypatch.setattr(trade_execution, "get_active_risk_pct", fake_get_active_risk_pct)

    with pytest.raises(HTTPException) as exc_info:
        await trade_execution.create_trade(
            db=db,
            user=user,
            symbol_id=3,
            strategy_id=2,
            side=TradeSideEnum.BUY,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
            quantity=Decimal("1"),
            trade_status=TradeStatusEnum.PENDING,
        )

    assert exc_info.value.status_code == 409
    assert "Daily trade limit reached" in exc_info.value.detail
    assert db.added == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_create_trade_rejects_when_active_risk_limit_is_exceeded(monkeypatch):
    user = User(id=11, email="trader@example.com", username="trader", hashed_password="x")
    mapping = UserPairStrategy(
        id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        risk_pct=Decimal("1.00"),
        max_trades_per_day=3,
        is_active=True,
    )
    strategy = Strategy(id=2, name=StrategyNameEnum.INTRADAY, htf="H4", ltf="M15", is_active=True)
    symbol = Symbol(id=3, exchange="binance", symbol="SOL/USDT", base_asset="SOL", quote_asset="USDT", is_active=True)
    db = FakeAsyncSession([mapping, strategy, symbol])

    async def fake_get_daily_trade_count(*args, **kwargs):
        return 0

    async def fake_get_active_risk_pct(*args, **kwargs):
        return Decimal("1.50")

    monkeypatch.setattr(trade_execution, "get_daily_trade_count", fake_get_daily_trade_count)
    monkeypatch.setattr(trade_execution, "get_active_risk_pct", fake_get_active_risk_pct)

    with pytest.raises(HTTPException) as exc_info:
        await trade_execution.create_trade(
            db=db,
            user=user,
            symbol_id=3,
            strategy_id=2,
            side=TradeSideEnum.BUY,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
            quantity=Decimal("1"),
            trade_status=TradeStatusEnum.OPEN,
        )

    assert exc_info.value.status_code == 409
    assert "Active account risk limit exceeded." == exc_info.value.detail
    assert db.added == []
    assert db.commits == 0
