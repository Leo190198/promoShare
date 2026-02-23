from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    enable_docs: bool = True

    jwt_secret: str = Field(..., min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_seconds: int = 86400
    jwt_issuer: str = "promoshare-api"

    admin_username: str = Field(..., min_length=1)
    admin_password: str = Field(..., min_length=1)

    shopee_app_id: str = Field(..., min_length=1)
    shopee_app_secret: str = Field(..., min_length=1)
    shopee_graphql_url: str = "https://open-api.affiliate.shopee.com.br/graphql"
    shopee_timeout_seconds: float = 20.0

    cache_enabled: bool = True
    cache_product_offers_ttl_seconds: int = 90
    cache_shop_offers_ttl_seconds: int = 90
    cache_maxsize: int = 256

    cors_enabled: bool = False
    cors_allow_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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
    def cors_allow_origins_list(self) -> list[str]:
        if not self.cors_allow_origins.strip():
            return []
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()

