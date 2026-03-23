from __future__ import annotations

import importlib

import anyio


def test_startup_skips_background_services_in_development(monkeypatch):
    main_module = importlib.import_module("trading_bot_backend.app.main")

    worker_calls: list[str] = []
    engine_calls: list[str] = []

    monkeypatch.setattr(main_module.settings, "enable_worker", False)
    monkeypatch.setattr(main_module.settings, "enable_demo_engine", False)
    monkeypatch.setattr(main_module, "start_worker", lambda: worker_calls.append("worker"))
    monkeypatch.setattr(main_module, "start_demo_engine", lambda: engine_calls.append("engine"))

    anyio.run(main_module.startup_event)

    assert worker_calls == []
    assert engine_calls == []


def test_startup_starts_background_services_when_enabled(monkeypatch):
    main_module = importlib.import_module("trading_bot_backend.app.main")

    worker_calls: list[str] = []
    engine_calls: list[str] = []

    monkeypatch.setattr(main_module.settings, "enable_worker", True)
    monkeypatch.setattr(main_module.settings, "enable_demo_engine", True)
    monkeypatch.setattr(main_module, "start_worker", lambda: worker_calls.append("worker"))
    monkeypatch.setattr(main_module, "start_demo_engine", lambda: engine_calls.append("engine"))

    anyio.run(main_module.startup_event)

    assert worker_calls == ["worker"]
    assert engine_calls == ["engine"]
