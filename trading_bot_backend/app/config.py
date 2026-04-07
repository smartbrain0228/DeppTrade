from functools import lru_cache

from pydantic import computed_field
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Market Operations Console"
    app_env: str = Field(default="development", alias="APP_ENV")
    enable_worker: bool | None = Field(default=None, alias="ENABLE_WORKER")
    enable_demo_engine: bool | None = Field(default=None, alias="ENABLE_DEMO_ENGINE")
    bootstrap_schema_on_startup: bool = Field(
        default=False, alias="BOOTSTRAP_SCHEMA_ON_STARTUP"
    )
    bootstrap_admin_on_startup: bool = Field(
        default=False, alias="BOOTSTRAP_ADMIN_ON_STARTUP"
    )
    market_data_mode: str = Field(default="live", alias="MARKET_DATA_MODE")
    market_data_mock_seed: int = Field(default=20260321, alias="MARKET_DATA_MOCK_SEED")

    database_url: str = Field(
        default="postgresql+asyncpg://app_user:app_password@localhost:5432/trading_bot",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")

    jwt_secret_key: str = Field(
        default="set-a-long-random-jwt-secret", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_minutes: int = Field(
        default=60 * 24 * 7, alias="REFRESH_TOKEN_EXPIRE_MINUTES"
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    mexc_api_key: str = Field(default="", alias="MEXC_API_KEY")
    mexc_api_secret: str = Field(default="", alias="MEXC_API_SECRET")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(
        default="set-a-strong-admin-password", alias="ADMIN_PASSWORD"
    )
    admin_session_secret: str = Field(
        default="set-a-long-random-admin-session-secret",
        alias="ADMIN_SESSION_SECRET",
    )

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    @computed_field
    @property
    def should_start_worker(self) -> bool:
        if self.enable_worker is not None:
            return self.enable_worker
        return self.app_env.lower() not in {"development", "dev", "test", "testing"}

    @computed_field
    @property
    def should_start_demo_engine(self) -> bool:
        if self.enable_demo_engine is not None:
            return self.enable_demo_engine
        return self.app_env.lower() not in {"development", "dev", "test", "testing"}

    @computed_field
    @property
    def use_mock_market_data(self) -> bool:
        return self.market_data_mode.lower().strip() in {"mock", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
