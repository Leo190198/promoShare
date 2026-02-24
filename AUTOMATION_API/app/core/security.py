from __future__ import annotations

from fastapi import Header

from app.core.config import get_settings
from app.core.exceptions import ApiException


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.automation_api_key:
        raise ApiException(status_code=401, code="unauthorized", message="Missing or invalid API key")

