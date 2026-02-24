from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    app_env: str = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    enable_docs: bool = True

    automation_api_key: str = Field(..., min_length=8)
    database_url: str = Field(..., min_length=1)

    automation_enabled: bool = True
    automation_tick_seconds: int = 30
    automation_timezone: str = "America/Sao_Paulo"
    automation_suggestion_interval_minutes: int = 30

    automation_default_group_id: str = ""
    automation_default_group_name: str = "Teste dos Posts Automaticos"
    automation_default_daily_target: int = 15
    automation_default_daily_limit: int = 15
    automation_default_start_time: str = "09:00"
    automation_default_end_time: str = "22:00"
    automation_default_theme_keywords: str = "iphone,notebook,fone bluetooth,ssd,smartwatch"
    automation_default_message_template: str = "🔥 {productName}\n💰 A partir de R$ {formattedPrice}\n🔗 {shortLink}"

    product_dedup_days: int = 7
    suggestion_fetch_limit_per_theme: int = 12
    suggestion_max_per_run: int = 30

    shopee_api_base_url: str = "https://promoshare-api.onrender.com"
    shopee_api_username: str = ""
    shopee_api_password: str = ""
    shopee_api_timeout_seconds: float = 20.0

    wa_api_base_url: str = "https://promoshare-whatsapp-api.onrender.com"
    wa_api_key: str = ""
    wa_api_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _normalize_postgres_url(value)

    @field_validator("automation_default_start_time", "automation_default_end_time")
    @classmethod
    def validate_hhmm(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("time must be HH:MM")
        hour, minute = parts
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError("time must be HH:MM")
        h = int(hour)
        m = int(minute)
        if h < 0 or h > 23 or m < 0 or m > 59:
            raise ValueError("time must be HH:MM")
        return f"{h:02d}:{m:02d}"

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.enable_docs else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.enable_docs else None

    @property
    def openapi_url(self) -> str | None:
        return "/openapi.json" if self.enable_docs else None

    @property
    def default_theme_keywords_list(self) -> list[str]:
        return [item.strip() for item in self.automation_default_theme_keywords.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()

