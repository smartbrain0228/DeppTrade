from __future__ import annotations

import httpx
import pytest

from trading_bot_backend.app.services import notifications


class DummyAsyncClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, timeout):
        if self.error is not None:
            raise self.error
        return self.response


class DummyResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


@pytest.mark.asyncio
async def test_send_telegram_message_logs_missing_config_once(monkeypatch):
    warnings: list[str] = []

    notifications._missing_config_logged = False
    notifications._reset_telegram_failure_state()
    monkeypatch.setattr(notifications.settings, "telegram_bot_token", "")
    monkeypatch.setattr(notifications.settings, "telegram_chat_id", "")
    monkeypatch.setattr(notifications.logger, "warning", lambda message, *args: warnings.append(message % args if args else message))

    await notifications.send_telegram_message("hello")
    await notifications.send_telegram_message("hello")

    assert warnings == ["Telegram not configured. Skipping notifications."]


@pytest.mark.asyncio
async def test_send_telegram_message_downgrades_repeated_network_failures_to_debug(monkeypatch):
    warnings: list[str] = []
    debugs: list[str] = []

    notifications._missing_config_logged = False
    notifications._reset_telegram_failure_state()
    monkeypatch.setattr(notifications.settings, "telegram_bot_token", "token")
    monkeypatch.setattr(notifications.settings, "telegram_chat_id", "chat")
    monkeypatch.setattr(
        notifications.httpx,
        "AsyncClient",
        lambda: DummyAsyncClient(error=httpx.ConnectError("All connection attempts failed")),
    )
    monkeypatch.setattr(notifications.logger, "warning", lambda message, *args: warnings.append(message % args if args else message))
    monkeypatch.setattr(notifications.logger, "debug", lambda message, *args: debugs.append(message % args if args else message))

    await notifications.send_telegram_message("hello")
    await notifications.send_telegram_message("hello")

    assert len(warnings) == 1
    assert "Failed to send Telegram notification" in warnings[0]
    assert len(debugs) == 1
    assert "Failed to send Telegram notification" in debugs[0]


@pytest.mark.asyncio
async def test_send_telegram_message_resets_failure_state_after_success(monkeypatch):
    warnings: list[str] = []

    notifications._missing_config_logged = False
    notifications._reset_telegram_failure_state()
    monkeypatch.setattr(notifications.settings, "telegram_bot_token", "token")
    monkeypatch.setattr(notifications.settings, "telegram_chat_id", "chat")
    monkeypatch.setattr(notifications.logger, "warning", lambda message, *args: warnings.append(message % args if args else message))

    clients = iter(
        [
            DummyAsyncClient(error=httpx.ConnectError("All connection attempts failed")),
            DummyAsyncClient(response=DummyResponse(200, "ok")),
            DummyAsyncClient(error=httpx.ConnectError("All connection attempts failed")),
        ]
    )
    monkeypatch.setattr(notifications.httpx, "AsyncClient", lambda: next(clients))

    await notifications.send_telegram_message("hello")
    await notifications.send_telegram_message("hello")
    await notifications.send_telegram_message("hello")

    assert len(warnings) == 2
    assert all("Failed to send Telegram notification" in item for item in warnings)
