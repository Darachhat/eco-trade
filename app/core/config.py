"""
app/core/config.py
──────────────────
Pydantic-Settings based configuration.
All values are read from environment variables (or .env file).
No secrets are hard-coded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import MarketCategory, TradingMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ─────────────────────────────────────────
    # Application
    # ─────────────────────────────────────────
    app_name: str = "ai_crypto_trader"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    app_secret_key: str = Field(..., min_length=32)

    # ─────────────────────────────────────────
    # Bybit
    # ─────────────────────────────────────────
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_testnet: bool = True
    bybit_category: MarketCategory = MarketCategory.LINEAR
    bybit_symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT"
    bybit_timeframes: str = "1,5,15,60,240"

    @property
    def symbols_list(self) -> list[str]:
        return [s.strip().upper() for s in self.bybit_symbols.split(",") if s.strip()]

    @property
    def timeframes_list(self) -> list[str]:
        return [t.strip() for t in self.bybit_timeframes.split(",") if t.strip()]

    # ─────────────────────────────────────────
    # Telegram
    # ─────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_admin_chat_id: str = ""

    # ─────────────────────────────────────────
    # Database
    # ─────────────────────────────────────────
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "ai_trader"
    postgres_user: str = ""
    postgres_password: str = ""
    database_url: str = ""

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    # ─────────────────────────────────────────
    # Redis
    # ─────────────────────────────────────────
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_url: str = ""

    @model_validator(mode="after")
    def assemble_redis_url(self) -> "Settings":
        if not self.redis_url:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            self.redis_url = f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return self

    # ─────────────────────────────────────────
    # Celery
    # ─────────────────────────────────────────
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    @model_validator(mode="after")
    def assemble_celery_urls(self) -> "Settings":
        if not self.celery_broker_url:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            self.celery_broker_url = (
                f"redis://{auth}{self.redis_host}:{self.redis_port}/1"
            )
        if not self.celery_result_backend:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            self.celery_result_backend = (
                f"redis://{auth}{self.redis_host}:{self.redis_port}/2"
            )
        return self

    # ─────────────────────────────────────────
    # ML
    # ─────────────────────────────────────────
    ml_model_path: str = "/app/models"
    ml_artifact_path: str = "/app/artifacts"
    mlflow_tracking_uri: str = "http://mlflow:5000"

    # ─────────────────────────────────────────
    # Prediction
    # ─────────────────────────────────────────
    prediction_horizons: str = "5,10,20,50"
    min_confidence: float = 0.75
    min_model_agreement: float = 0.70
    min_risk_reward: float = 2.0

    @property
    def horizons_list(self) -> list[int]:
        return [int(h.strip()) for h in self.prediction_horizons.split(",") if h.strip()]

    # ─────────────────────────────────────────
    # Risk
    # ─────────────────────────────────────────
    risk_per_trade: float = 0.01
    max_daily_loss: float = 0.03
    max_open_positions: int = 3
    max_consecutive_losses: int = 5

    # ─────────────────────────────────────────
    # Trading Mode
    # ─────────────────────────────────────────
    trading_mode: TradingMode = TradingMode.PAPER
    live_execution_enabled: bool = False

    @property
    def is_live(self) -> bool:
        return (
            self.trading_mode == TradingMode.LIVE
            and self.live_execution_enabled is True
        )

    # ─────────────────────────────────────────
    # Self-Learning
    # ─────────────────────────────────────────
    retrain_enabled: bool = True
    retrain_interval_hours: int = 24
    min_training_samples: int = 10_000
    model_performance_window: int = 100
    challenger_enabled: bool = True

    # ─────────────────────────────────────────
    # Signal Quality
    # ─────────────────────────────────────────
    min_signal_quality_score: int = 65

    # ─────────────────────────────────────────
    # Monitoring
    # ─────────────────────────────────────────
    prometheus_port: int = 9090
    grafana_port: int = 3000

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Use this everywhere."""
    return Settings()


# Convenience alias
settings = get_settings()
