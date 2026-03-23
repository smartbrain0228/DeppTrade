from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from trading_bot_backend.app.models import Strategy, StrategyNameEnum, Symbol, Trade, TradeSideEnum, TradeStatusEnum
from trading_bot_backend.app.services.trade_execution import (
    assert_valid_status_transition,
    get_active_risk_pct,
    get_daily_trade_count,
    get_trade_for_user,
    list_user_trades,
    normalize_closed_at,
    update_trade,
    validate_trade_levels,
)


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeAsyncSession:
    def __init__(self, results):
        self.results = list(results)
        self.commits = 0
        self.refreshes = 0
        self.statements = []

    async def execute(self, stmt):
        if not self.results:
            raise AssertionError("Unexpected execute() call in test.")
        self.statements.append(stmt)
        return FakeScalarResult(self.results.pop(0))

    async def commit(self):
        self.commits += 1

    async def refresh(self, _instance):
        self.refreshes += 1


def build_trade(*, status: TradeStatusEnum = TradeStatusEnum.PENDING) -> Trade:
    trade = Trade(
        id=55,
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


def test_validate_trade_levels_rejects_invalid_buy_levels():
    with pytest.raises(HTTPException) as exc_info:
        validate_trade_levels(
            entry_price=Decimal("100"),
            stop_loss=Decimal("100"),
            take_profit=Decimal("110"),
            side=TradeSideEnum.BUY,
        )

    assert exc_info.value.status_code == 422
    assert "stop_loss must be below entry_price" in exc_info.value.detail


def test_validate_trade_levels_rejects_invalid_sell_levels():
    with pytest.raises(HTTPException) as exc_info:
        validate_trade_levels(
            entry_price=Decimal("100"),
            stop_loss=Decimal("105"),
            take_profit=Decimal("100"),
            side=TradeSideEnum.SELL,
        )

    assert exc_info.value.status_code == 422
    assert "take_profit must be below entry_price" in exc_info.value.detail


def test_assert_valid_status_transition_rejects_invalid_transition():
    with pytest.raises(HTTPException) as exc_info:
        assert_valid_status_transition(TradeStatusEnum.CLOSED, TradeStatusEnum.OPEN)

    assert exc_info.value.status_code == 409
    assert "CLOSED -> OPEN" in exc_info.value.detail


def test_normalize_closed_at_clamps_before_opened_at():
    trade = build_trade()
    closed_at = datetime(2026, 3, 13, 9, 30, tzinfo=timezone.utc)

    normalized = normalize_closed_at(trade, closed_at)

    assert normalized == trade.opened_at


@pytest.mark.asyncio
async def test_get_trade_for_user_returns_matching_trade():
    trade = build_trade()
    db = FakeAsyncSession([trade])

    result = await get_trade_for_user(db, trade_id=55, user_id=11)

    assert result is trade
    where_sql = str(db.statements[0].whereclause)
    assert "trades.id" in where_sql
    assert "trades.user_id" in where_sql


@pytest.mark.asyncio
async def test_list_user_trades_returns_all_trades_without_status_filter():
    trades = [build_trade(status=TradeStatusEnum.OPEN), build_trade(status=TradeStatusEnum.PENDING)]
    db = FakeAsyncSession([trades])

    result = await list_user_trades(db, user_id=11, limit=25)

    assert result == trades
    where_sql = str(db.statements[0].whereclause)
    assert "trades.user_id" in where_sql
    assert "trades.status" not in where_sql


@pytest.mark.asyncio
async def test_list_user_trades_applies_status_filter_when_provided():
    trades = [build_trade(status=TradeStatusEnum.CLOSED)]
    db = FakeAsyncSession([trades])

    result = await list_user_trades(db, user_id=11, status_filter=TradeStatusEnum.CLOSED, limit=10)

    assert result == trades
    where_sql = str(db.statements[0].whereclause)
    assert "trades.user_id" in where_sql
    assert "trades.status" in where_sql


@pytest.mark.asyncio
async def test_get_daily_trade_count_returns_scalar_count():
    db = FakeAsyncSession([3])

    result = await get_daily_trade_count(db, user_id=11, symbol_id=3, strategy_id=2)

    assert result == 3
    where_sql = str(db.statements[0].whereclause)
    assert "trades.user_id" in where_sql
    assert "trades.symbol_id" in where_sql
    assert "trades.strategy_id" in where_sql


@pytest.mark.asyncio
async def test_get_active_risk_pct_normalizes_numeric_result_to_decimal():
    db = FakeAsyncSession([1.5])

    result = await get_active_risk_pct(db, user_id=11)

    assert result == Decimal("1.5")


@pytest.mark.asyncio
async def test_get_active_risk_pct_keeps_decimal_result():
    db = FakeAsyncSession([Decimal("1.25")])

    result = await get_active_risk_pct(db, user_id=11)

    assert result == Decimal("1.25")


@pytest.mark.asyncio
async def test_update_trade_sets_closed_timestamp_when_closing(monkeypatch):
    trade = build_trade(status=TradeStatusEnum.OPEN)
    refreshed_trade = build_trade(status=TradeStatusEnum.CLOSED)
    refreshed_trade.closed_at = datetime(2026, 3, 13, 11, 0, tzinfo=timezone.utc)
    db = FakeAsyncSession([refreshed_trade])
    fixed_now = datetime(2026, 3, 13, 11, 0, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is not None else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr("trading_bot_backend.app.services.trade_execution.datetime", FixedDateTime)

    result = await update_trade(
        db=db,
        trade=trade,
        status_value=TradeStatusEnum.CLOSED,
    )

    assert trade.status == TradeStatusEnum.CLOSED
    assert trade.closed_at == fixed_now
    assert result.status == TradeStatusEnum.CLOSED
    assert db.commits == 1
    assert db.refreshes == 1


@pytest.mark.asyncio
async def test_update_trade_uses_normalized_explicit_closed_at_and_updates_levels():
    trade = build_trade(status=TradeStatusEnum.OPEN)
    refreshed_trade = build_trade(status=TradeStatusEnum.CLOSED)
    refreshed_trade.stop_loss = Decimal("96")
    refreshed_trade.take_profit = Decimal("112")
    refreshed_trade.closed_at = trade.opened_at
    db = FakeAsyncSession([refreshed_trade])
    explicit_closed_at = datetime(2026, 3, 13, 8, 0, tzinfo=timezone.utc)

    result = await update_trade(
        db=db,
        trade=trade,
        status_value=TradeStatusEnum.CLOSED,
        stop_loss=Decimal("96"),
        take_profit=Decimal("112"),
        pnl=Decimal("8.5"),
        closed_at=explicit_closed_at,
    )

    assert trade.stop_loss == Decimal("96")
    assert trade.take_profit == Decimal("112")
    assert trade.pnl == Decimal("8.5")
    assert trade.closed_at == trade.opened_at
    assert result.closed_at == trade.opened_at
    assert db.commits == 1
    assert db.refreshes == 1
