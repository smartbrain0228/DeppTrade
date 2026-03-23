from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from trading_bot_backend.app.models import Strategy, StrategyNameEnum, Symbol, Trade, TradeSideEnum, TradeStatusEnum, User
from trading_bot_backend.app.routes import signals as signals_routes
from trading_bot_backend.app.routes import trades as trades_routes
from trading_bot_backend.app.users.deps import get_current_user


def build_trade(*, trade_id: int = 55, status: TradeStatusEnum = TradeStatusEnum.PENDING) -> Trade:
    trade = Trade(
        id=trade_id,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.INTRADAY,
        side=TradeSideEnum.BUY,
        status=status,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("110"),
        quantity=Decimal("1"),
        opened_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
    )
    trade.symbol = Symbol(id=3, exchange="binance", symbol="SOL/USDT", base_asset="SOL", quote_asset="USDT")
    trade.strategy = Strategy(id=2, name=StrategyNameEnum.INTRADAY, htf="H4", ltf="M15")
    return trade


def build_test_app(*routers) -> FastAPI:
    app = FastAPI()

    async def fake_current_user():
        return User(id=11, email="trader@example.com", username="trader", hashed_password="x")

    app.dependency_overrides[get_current_user] = fake_current_user

    async def fake_db():
        yield object()

    app.dependency_overrides[signals_routes.get_db] = fake_db
    app.dependency_overrides[trades_routes.get_db] = fake_db

    for router in routers:
        app.include_router(router)

    return app


@pytest.mark.asyncio
async def test_preview_strategy_returns_analysis_payload(monkeypatch):
    app = build_test_app(signals_routes.router)
    expected = {"signal": {"status": "READY", "reason": "ok"}}

    def fake_analyze_strategy(**kwargs):
        assert kwargs["strategy_name"] == StrategyNameEnum.INTRADAY
        return expected

    monkeypatch.setattr(signals_routes, "analyze_strategy", fake_analyze_strategy)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/signals/preview",
            json={
                "strategy": "INTRADAY",
                "htf_candles": [{"time": 1, "open": 1, "high": 2, "low": 1, "close": 2, "volume": 1}],
                "ltf_candles": [{"time": 1, "open": 1, "high": 2, "low": 1, "close": 2, "volume": 1}],
            },
        )

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.asyncio
async def test_scan_assignment_signal_returns_422_when_service_raises_value_error(monkeypatch):
    app = build_test_app(signals_routes.router)

    async def fake_analyze_assignment_signal(*args, **kwargs):
        raise ValueError("bad candles")

    monkeypatch.setattr(signals_routes, "analyze_assignment_signal", fake_analyze_assignment_signal)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/signals/assignments/7/scan", json={"htf_limit": 120, "ltf_limit": 240})

    assert response.status_code == 422
    assert response.json()["detail"] == "bad candles"


@pytest.mark.asyncio
async def test_execute_assignment_trade_returns_created_payload(monkeypatch):
    app = build_test_app(signals_routes.router)
    expected = {
        "analysis": {"signal": {"status": "READY", "reason": "aligned"}},
        "trade": {"id": 9, "status": "PENDING"},
    }

    async def fake_execute_assignment_signal(*args, **kwargs):
        assert kwargs["assignment_id"] == 7
        assert kwargs["quantity"] == Decimal("1.5")
        assert kwargs["trade_status"] == TradeStatusEnum.PENDING
        return expected

    monkeypatch.setattr(signals_routes, "execute_assignment_signal", fake_execute_assignment_signal)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/signals/assignments/7/execute", json={"quantity": "1.5", "status": "PENDING"})

    assert response.status_code == 201
    assert response.json() == {"analysis": {"signal": {"status": "READY", "reason": "aligned"}}, "trade": {"id": 9, "status": "PENDING"}}


@pytest.mark.asyncio
async def test_create_trade_route_returns_created_trade_payload(monkeypatch):
    app = build_test_app(trades_routes.router)
    trade = build_trade(trade_id=77)

    async def fake_create_trade_service(*args, **kwargs):
        assert kwargs["symbol_id"] == 3
        assert kwargs["strategy_id"] == 2
        assert kwargs["side"] == TradeSideEnum.BUY
        return trade

    monkeypatch.setattr(trades_routes, "create_trade_service", fake_create_trade_service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/trades",
            json={
                "symbol_id": 3,
                "strategy_id": 2,
                "side": "BUY",
                "entry_price": "100",
                "stop_loss": "95",
                "take_profit": "110",
                "quantity": "1",
                "status": "PENDING",
            },
        )

    assert response.status_code == 201
    assert response.json()["id"] == 77
    assert response.json()["symbol"] == "SOL/USDT"
    assert response.json()["strategy_name"] == "INTRADAY"


@pytest.mark.asyncio
async def test_list_my_trades_route_applies_status_filter(monkeypatch):
    app = build_test_app(trades_routes.router)
    trade = build_trade(trade_id=1, status=TradeStatusEnum.OPEN)

    async def fake_list_user_trades(*args, **kwargs):
        assert kwargs["user_id"] == 11
        assert kwargs["status_filter"] == TradeStatusEnum.OPEN
        assert kwargs["limit"] == 25
        return [trade]

    monkeypatch.setattr(trades_routes, "list_user_trades", fake_list_user_trades)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/trades", params={"status": "OPEN", "limit": 25})

    assert response.status_code == 200
    assert response.json()[0]["status"] == "OPEN"


@pytest.mark.asyncio
async def test_get_trade_route_returns_404_when_trade_is_missing(monkeypatch):
    app = build_test_app(trades_routes.router)

    async def fake_get_trade_for_user(*args, **kwargs):
        return None

    monkeypatch.setattr(trades_routes, "get_trade_for_user", fake_get_trade_for_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/trades/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trade not found."


@pytest.mark.asyncio
async def test_update_trade_route_returns_updated_trade(monkeypatch):
    app = build_test_app(trades_routes.router)
    trade = build_trade(trade_id=55, status=TradeStatusEnum.OPEN)
    updated_trade = build_trade(trade_id=55, status=TradeStatusEnum.CLOSED)
    updated_trade.closed_at = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)

    async def fake_get_trade_for_user(*args, **kwargs):
        return trade

    async def fake_update_trade_service(*args, **kwargs):
        assert kwargs["trade"] is trade
        assert kwargs["status_value"] == TradeStatusEnum.CLOSED
        assert kwargs["pnl"] == Decimal("10.5")
        return updated_trade

    monkeypatch.setattr(trades_routes, "get_trade_for_user", fake_get_trade_for_user)
    monkeypatch.setattr(trades_routes, "update_trade_service", fake_update_trade_service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch("/trades/55", json={"status": "CLOSED", "pnl": "10.5"})

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    assert response.json()["closed_at"] == "2026-03-13T12:00:00+00:00"


@pytest.mark.asyncio
async def test_update_trade_route_returns_404_when_trade_is_missing(monkeypatch):
    app = build_test_app(trades_routes.router)

    async def fake_get_trade_for_user(*args, **kwargs):
        return None

    monkeypatch.setattr(trades_routes, "get_trade_for_user", fake_get_trade_for_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch("/trades/55", json={"status": "CLOSED"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Trade not found."
