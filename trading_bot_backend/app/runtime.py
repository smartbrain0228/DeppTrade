import logging

from trading_bot_backend.app.config import settings
from trading_bot_backend.app.services.demo_engine import (
    is_demo_engine_running,
    start_demo_engine,
)
from trading_bot_backend.app.worker import is_worker_running, start_worker

logger = logging.getLogger(__name__)


def wake_background_services() -> dict[str, bool]:
    worker_started = False
    demo_engine_started = False

    if settings.should_start_worker and not is_worker_running():
        worker_started = start_worker()
        if worker_started:
            logger.info("Trade worker started from wake-up trigger")

    if settings.should_start_demo_engine and not is_demo_engine_running():
        demo_engine_started = start_demo_engine()
        if demo_engine_started:
            logger.info("Demo engine started from wake-up trigger")

    return {
        "worker_enabled": settings.should_start_worker,
        "worker_running": is_worker_running(),
        "worker_started": worker_started,
        "demo_engine_enabled": settings.should_start_demo_engine,
        "demo_engine_running": is_demo_engine_running(),
        "demo_engine_started": demo_engine_started,
    }
