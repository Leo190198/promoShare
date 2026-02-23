from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ApiException

bearer_scheme = HTTPBearer(auto_error=False)


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return secrets.compare_digest(username, settings.admin_username) and secrets.compare_digest(
        password, settings.admin_password
    )


def create_access_token(*, subject: str, username: str) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_delta = timedelta(seconds=settings.jwt_access_token_expires_seconds)
    expire_at = now + expires_delta
    claims = {
        "sub": subject,
        "username": username,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_access_token_expires_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiException(status_code=401, code="token_expired", message="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ApiException(status_code=401, code="invalid_token", message="Invalid token") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiException(status_code=401, code="unauthorized", message="Missing bearer token")
    return decode_access_token(credentials.credentials)

