import httpx
import logging
from typing import Any, Dict, Optional
from trading_bot_backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_missing_config_logged = False
_last_failure_fingerprint: str | None = None


def _log_telegram_failure_once(message: str, *, fingerprint: str) -> None:
    global _last_failure_fingerprint
    if _last_failure_fingerprint == fingerprint:
        logger.debug(message)
        return
    _last_failure_fingerprint = fingerprint
    logger.warning("%s Repeated failures will be logged at debug level until recovery.", message)


def _reset_telegram_failure_state() -> None:
    global _last_failure_fingerprint
    _last_failure_fingerprint = None

async def send_telegram_message(text: str, reply_markup: Optional[Dict[str, Any]] = None):
    """
    Sends a message to the configured Telegram chat.
    """
    global _missing_config_logged
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        if not _missing_config_logged:
            logger.warning("Telegram not configured. Skipping notifications.")
            _missing_config_logged = True
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                _log_telegram_failure_once(
                    f"Telegram API error ({response.status_code}): {response.text}",
                    fingerprint=f"status:{response.status_code}:{response.text}",
                )
                return
            _reset_telegram_failure_state()
    except Exception as e:
        _log_telegram_failure_once(
            f"Failed to send Telegram notification: {e}",
            fingerprint=f"exception:{type(e).__name__}:{e}",
        )
