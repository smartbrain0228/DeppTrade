from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from trading_bot_backend.app.models import SignalEvent
from trading_bot_backend.app.services.signal_history import signal_event_to_dict


def _overlay_marker(kind: str, event: dict | None, *, price_key: str, label: str) -> dict | None:
    if event is None:
        return None
    return {
        "kind": kind,
        "label": label,
        "time": event.get("candle_time"),
        "price": event.get(price_key),
        "payload": event,
    }


def _overlay_zone(kind: str, zone: dict | None) -> dict | None:
    if zone is None:
        return None
    return {
        "kind": kind,
        "lower_price": zone.get("lower_price"),
        "upper_price": zone.get("upper_price"),
        "midpoint": zone.get("midpoint"),
    }


def build_signal_overlay_item(event: SignalEvent) -> dict:
    analysis = event.analysis or {}
    assignment = analysis.get("assignment", {})
    signal = analysis.get("signal", {})
    ltf_events = analysis.get("ltf_events", {})
    entry_plan = analysis.get("entry_plan", {})
    trade_plan = signal.get("trade_plan")
    sweep = ltf_events.get("sweep")
    mss = ltf_events.get("mss")
    fvg = ltf_events.get("fvg")

    markers = [
        marker
        for marker in (
            _overlay_marker("SWEEP", sweep, price_key="swept_price", label="Liquidity sweep"),
            _overlay_marker("MSS", mss, price_key="pivot_price", label="Market structure shift"),
            _overlay_marker("FVG", fvg, price_key="midpoint", label="Fair value gap"),
        )
        if marker is not None
    ]
    zones = [zone for zone in (_overlay_zone("ENTRY", entry_plan.get("entry_zone")), _overlay_zone("FVG", fvg)) if zone is not None]

    return {
        **signal_event_to_dict(event),
        "symbol": assignment.get("symbol"),
        "exchange": assignment.get("exchange"),
        "strategy_name": assignment.get("strategy_name"),
        "timeframes": analysis.get("timeframes"),
        "timeline": {
            "bias_time": None,
            "sweep_time": sweep.get("candle_time") if sweep else None,
            "mss_time": mss.get("candle_time") if mss else None,
            "fvg_time": fvg.get("candle_time") if fvg else None,
            "entry_ready_time": fvg.get("candle_time") if signal.get("status") == "READY" and fvg else None,
        },
        "markers": markers,
        "zones": zones,
        "levels": {
            "entry_price": trade_plan.get("entry_price") if trade_plan else None,
            "stop_loss": trade_plan.get("stop_loss") if trade_plan else None,
            "take_profit": trade_plan.get("take_profit") if trade_plan else None,
        },
        "htf_pivots": analysis.get("htf_pivots"),
        "ltf_pivots": analysis.get("ltf_pivots"),
        "entry_plan": entry_plan,
        "trade_plan": trade_plan,
    }


def build_assignment_overlay_payload(
    *,
    assignment_id: int,
    total: int,
    offset: int,
    limit: int,
    events: Iterable[SignalEvent],
) -> dict:
    overlay_items = [build_signal_overlay_item(event) for event in events]
    latest = overlay_items[0] if overlay_items else None
    timeline_items = list(reversed(overlay_items))

    return {
        "assignment_id": assignment_id,
        "total": total,
        "count": len(overlay_items),
        "offset": offset,
        "limit": limit,
        "latest": latest,
        "timeline": timeline_items,
    }
