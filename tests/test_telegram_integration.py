from __future__ import annotations

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
    UserPairStrategy,
)
from trading_bot_backend.app.services.telegram_templates import (
    get_interactive_keyboard,
    get_trade_opened_template,
)
from trading_bot_backend.app.services.trade_management import apply_trade_management


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeAsyncSession:
    def __init__(self, assignment: UserPairStrategy | None):
        self.assignment = assignment
        self.commits = 0

    async def execute(self, _stmt):
        return FakeScalarResult(self.assignment)

    async def commit(self):
        self.commits += 1


def build_trade(*, side: TradeSideEnum = TradeSideEnum.BUY) -> Trade:
    trade = Trade(
        id=77,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.SMC_INTRADAY,
        side=side,
        status=TradeStatusEnum.OPEN,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95") if side == TradeSideEnum.BUY else Decimal("105"),
        take_profit=Decimal("110") if side == TradeSideEnum.BUY else Decimal("90"),
        quantity=Decimal("2"),
        is_demo=True,
        opened_at=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
    )
    trade.symbol = Symbol(id=3, exchange="binance", symbol="BTC/USDT", base_asset="BTC", quote_asset="USDT")
    trade.strategy = Strategy(id=2, name=StrategyNameEnum.SMC_INTRADAY, htf="H4", ltf="M15")
    return trade


@pytest.mark.asyncio
async def test_apply_trade_management_updates_assignment_balance_and_sends_message(monkeypatch):
    trade = build_trade()
    assignment = UserPairStrategy(
        id=9,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        risk_pct=Decimal("1.0"),
        max_trades_per_day=1,
        is_active=True,
        demo_balance=Decimal("100.0"),
        trade_count=0,
        is_paused=False,
    )
    db = FakeAsyncSession(assignment)
    sent_messages: list[str] = []

    async def fake_send_telegram_message(message: str, reply_markup=None):
        assert reply_markup is None
        sent_messages.append(message)

    monkeypatch.setattr(
        "trading_bot_backend.app.services.trade_management.send_telegram_message",
        fake_send_telegram_message,
    )

    updated = await apply_trade_management(
        db,
        trade,
        [{"time": 1, "open": 100, "high": 111, "low": 99, "close": 108, "volume": 1}],
    )

    assert updated is True
    assert trade.status == TradeStatusEnum.CLOSED
    assert trade.exit_price == Decimal("110")
    assert trade.pnl == Decimal("20")
    assert assignment.demo_balance == Decimal("120.0")
    assert db.commits == 1
    assert len(sent_messages) == 1
    assert "TRADE FERME" in sent_messages[0]
    assert "Intraday H4/M15" in sent_messages[0]
    assert "120.00 USDT" in sent_messages[0]


def test_get_interactive_keyboard_exposes_only_safe_url_button():
    keyboard = get_interactive_keyboard(55)

    assert keyboard == {
        "inline_keyboard": [
            [
                {"text": "Voir graphique", "url": "https://tradingview.com/chart/"},
            ]
        ]
    }


def test_get_trade_opened_template_uses_professional_strategy_label():
    message = get_trade_opened_template(
        strategy_name=StrategyNameEnum.SMC_H1_M5,
        symbol="BTCUSDT",
        side="BUY",
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=105.0,
        balance=250.0,
        quantity=1.25,
        risk_pct=1.0,
        mode="Demo",
    )

    assert "TRADE OUVERT" in message
    assert "Scalping H1/M5" in message
    assert "Quantite" in message
    assert "Risque" in message
