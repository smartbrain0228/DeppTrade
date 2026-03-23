from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_bot_backend.app.models import (
    SignalEvent,
    SignalStatusEnum,
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
from trading_bot_backend.app.services.signal_history import (
    _apply_signal_event_filters,
    _normalize_json_value,
    create_signal_event,
    signal_event_to_admin_dict,
    signal_event_to_dict,
)
from trading_bot_backend.app.services.signal_overlays import (
    build_assignment_overlay_payload,
    build_signal_overlay_item,
)


class FakeAsyncSession:
    def __init__(self):
        self.added = []

    def add(self, instance):
        self.added.append(instance)

    async def commit(self):
        return None

    async def refresh(self, instance):
        instance.id = 1
        if instance.created_at is None:
            instance.created_at = datetime(2026, 3, 12, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_create_signal_event_normalizes_analysis_and_side():
    db = FakeAsyncSession()
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
            "reason": "Setup confirmed.",
            "side": "BUY",
            "trade_plan": {"side": TradeSideEnum.BUY},
        },
    }

    event = await create_signal_event(db, analysis=analysis, trigger=SignalTriggerEnum.SCAN)

    assert len(db.added) == 1
    assert event.signal_status == SignalStatusEnum.READY
    assert event.side == TradeSideEnum.BUY
    assert event.analysis["signal"]["trade_plan"]["side"] == "BUY"


def test_signal_event_to_dict_returns_api_shape():
    event = SignalEvent(
        id=9,
        assignment_id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        trade_id=15,
        trigger=SignalTriggerEnum.EXECUTE,
        signal_status=SignalStatusEnum.READY,
        signal_reason="Setup confirmed.",
        side=TradeSideEnum.BUY,
        htf_bias="bullish",
        analysis={"signal": {"status": "READY"}},
        created_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )

    payload = signal_event_to_dict(event)

    assert payload["id"] == 9
    assert payload["trigger"] == "EXECUTE"
    assert payload["signal_status"] == "READY"
    assert payload["side"] == "BUY"


def test_signal_event_to_admin_dict_returns_enriched_shape():
    event = SignalEvent(
        id=9,
        assignment_id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        trade_id=15,
        trigger=SignalTriggerEnum.EXECUTE,
        signal_status=SignalStatusEnum.READY,
        signal_reason="Setup confirmed.",
        side=TradeSideEnum.BUY,
        htf_bias="bullish",
        analysis={"signal": {"status": "READY"}},
        created_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )
    event.user = User(id=11, email="admin@example.com", username="admin", hashed_password="x")
    event.symbol = Symbol(id=3, exchange="binance", symbol="SOL/USDT", base_asset="SOL", quote_asset="USDT")
    event.strategy = Strategy(id=2, name=StrategyNameEnum.INTRADAY, htf="H4", ltf="M15")
    event.trade = Trade(
        id=15,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        tag=StrategyNameEnum.INTRADAY,
        side=TradeSideEnum.BUY,
        status=TradeStatusEnum.PENDING,
        entry_price=Decimal("1"),
        stop_loss=Decimal("0.5"),
        take_profit=Decimal("2"),
        quantity=Decimal("1"),
    )
    event.assignment = UserPairStrategy(
        id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        risk_pct=Decimal("1.00"),
        max_trades_per_day=1,
        is_active=True,
    )

    payload = signal_event_to_admin_dict(event)

    assert payload["username"] == "admin"
    assert payload["symbol"] == "SOL/USDT"
    assert payload["exchange"] == "binance"
    assert payload["strategy_name"] == "INTRADAY"
    assert payload["assignment_active"] is True
    assert payload["trade_status"] == "PENDING"


def test_build_signal_overlay_item_returns_chart_ready_payload():
    event = SignalEvent(
        id=21,
        assignment_id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        trade_id=None,
        trigger=SignalTriggerEnum.SCAN,
        signal_status=SignalStatusEnum.READY,
        signal_reason="Setup confirmed.",
        side=TradeSideEnum.BUY,
        htf_bias="bullish",
        analysis={
            "assignment": {
                "symbol": "SOL/USDT",
                "exchange": "binance",
                "strategy_name": "INTRADAY",
            },
            "timeframes": {"htf": "H4", "ltf": "M15"},
            "signal": {
                "status": "READY",
                "trade_plan": {
                    "entry_price": 100.75,
                    "stop_loss": 97.0,
                    "take_profit": 110.0,
                },
            },
            "ltf_events": {
                "sweep": {"candle_time": 100, "swept_price": 98.5},
                "mss": {"candle_time": 110, "pivot_price": 101.0},
                "fvg": {
                    "candle_time": 120,
                    "lower_price": 100.0,
                    "upper_price": 101.5,
                    "midpoint": 100.75,
                },
            },
            "entry_plan": {
                "entry_zone": {
                    "lower_price": 100.0,
                    "upper_price": 101.5,
                    "midpoint": 100.75,
                }
            },
            "htf_pivots": {"highs": [], "lows": []},
            "ltf_pivots": {"highs": [], "lows": []},
        },
        created_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )

    payload = build_signal_overlay_item(event)

    assert payload["symbol"] == "SOL/USDT"
    assert payload["timeline"]["sweep_time"] == 100
    assert payload["timeline"]["entry_ready_time"] == 120
    assert len(payload["markers"]) == 3
    assert payload["levels"]["entry_price"] == 100.75
    assert len(payload["zones"]) == 2


def test_build_assignment_overlay_payload_reverses_timeline_order():
    older = SignalEvent(
        id=1,
        assignment_id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        trade_id=None,
        trigger=SignalTriggerEnum.SCAN,
        signal_status=SignalStatusEnum.WAITING_SWEEP,
        signal_reason="Waiting.",
        side=None,
        htf_bias="bullish",
        analysis={"assignment": {}, "signal": {"status": "WAITING_SWEEP"}, "ltf_events": {}, "entry_plan": {}},
        created_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
    )
    newer = SignalEvent(
        id=2,
        assignment_id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        trade_id=None,
        trigger=SignalTriggerEnum.SCAN,
        signal_status=SignalStatusEnum.READY,
        signal_reason="Ready.",
        side=TradeSideEnum.BUY,
        htf_bias="bullish",
        analysis={"assignment": {}, "signal": {"status": "READY"}, "ltf_events": {}, "entry_plan": {}},
        created_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )

    payload = build_assignment_overlay_payload(
        assignment_id=7,
        total=2,
        offset=0,
        limit=50,
        events=[newer, older],
    )

    assert payload["latest"]["id"] == 2
    assert payload["timeline"][0]["id"] == 1
    assert payload["timeline"][1]["id"] == 2


def test_normalize_json_value_converts_nested_enums_and_datetimes():
    value = {
        "side": TradeSideEnum.SELL,
        "items": [datetime(2026, 3, 12, tzinfo=timezone.utc)],
    }

    normalized = _normalize_json_value(value)

    assert normalized == {
        "side": "SELL",
        "items": ["2026-03-12T00:00:00+00:00"],
    }


def test_apply_signal_event_filters_adds_all_requested_predicates():
    stmt = _apply_signal_event_filters(
        SignalEvent.__table__.select(),
        assignment_id=7,
        user_id=11,
        symbol_id=3,
        strategy_id=2,
        signal_status=SignalStatusEnum.READY,
        trigger=SignalTriggerEnum.EXECUTE,
        created_from=datetime(2026, 3, 10, tzinfo=timezone.utc),
        created_to=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )

    where_sql = str(stmt.whereclause)

    assert "signal_events.assignment_id" in where_sql
    assert "signal_events.user_id" in where_sql
    assert "signal_events.symbol_id" in where_sql
    assert "signal_events.strategy_id" in where_sql
    assert "signal_events.signal_status" in where_sql
    assert "signal_events.trigger" in where_sql
    assert "signal_events.created_at" in where_sql
