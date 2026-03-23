import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from trading_bot_backend.app.admin import setup_admin
from trading_bot_backend.app.config import settings
from trading_bot_backend.app.routes.admin_config import router as admin_config_router
from trading_bot_backend.app.routes.auth import router as auth_router
from trading_bot_backend.app.routes.market import router as market_router
from trading_bot_backend.app.routes.portal import router as portal_router
from trading_bot_backend.app.routes.signals import router as signals_router
from trading_bot_backend.app.routes.trades import router as trades_router
from trading_bot_backend.app.routes.backtest import router as backtest_router
from trading_bot_backend.app.services.binance import router as binance_router
from trading_bot_backend.app.websocket import router as websocket_router
from trading_bot_backend.app.worker import start_worker
from trading_bot_backend.app.services.demo_engine import start_demo_engine

async def startup_event():
    logger.info("Bot started")
    logger.info("Market data connected")
    if settings.should_start_worker:
        start_worker()
        logger.info("Trade worker started")
    else:
        logger.info("Trade worker disabled for this environment")

    if settings.should_start_demo_engine:
        start_demo_engine()
        logger.info("Demo engine started")
    else:
        logger.info("Demo engine disabled for this environment")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await startup_event()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Simplified for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.admin_session_secret)

app.include_router(binance_router)
app.include_router(auth_router)
app.include_router(admin_config_router)
app.include_router(market_router)
app.include_router(portal_router)
app.include_router(signals_router)
app.include_router(trades_router)
app.include_router(backtest_router)
app.include_router(websocket_router)

setup_admin(app)

# --- Serve Frontend Locally ---
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
    logger.info(f"Frontend served from {frontend_path}")
else:
    @app.get("/")
    def read_root():
        return {"message": "Bot Trading Copilot backend is running (Frontend not built)"}
    logger.warning("Frontend 'dist' folder not found. Run 'npm run build' in frontend directory to serve it via backend.")
