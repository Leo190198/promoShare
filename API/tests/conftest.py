from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Configure required env vars before importing app settings/app.
os.environ.setdefault("JWT_SECRET", "test-secret-1234567890")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", "86400")
os.environ.setdefault("JWT_ISSUER", "promoshare-api")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass")
os.environ.setdefault("SHOPEE_APP_ID", "123456")
os.environ.setdefault("SHOPEE_APP_SECRET", "demo-secret")
os.environ.setdefault("SHOPEE_GRAPHQL_URL", "https://open-api.affiliate.shopee.com.br/graphql")
os.environ.setdefault("CACHE_ENABLED", "true")
os.environ.setdefault("CACHE_PRODUCT_OFFERS_TTL_SECONDS", "90")
os.environ.setdefault("CACHE_SHOP_OFFERS_TTL_SECONDS", "90")
os.environ.setdefault("CACHE_MAXSIZE", "256")
os.environ.setdefault("ENABLE_DOCS", "true")

from app.core.cache import reset_cache_manager  # noqa: E402
from app.core.config import reset_settings_cache  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    reset_settings_cache()
    reset_cache_manager()
    yield
    reset_cache_manager()


@pytest.fixture
def client() -> TestClient:
    reset_settings_cache()
    reset_cache_manager()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass"})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}

