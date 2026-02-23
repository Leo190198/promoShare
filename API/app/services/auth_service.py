from __future__ import annotations

from app.core.exceptions import ApiException
from app.core.security import create_access_token, verify_admin_credentials
from app.schemas.auth import LoginTokenData


def login_user(*, username: str, password: str) -> LoginTokenData:
    if not verify_admin_credentials(username, password):
        raise ApiException(status_code=401, code="invalid_credentials", message="Invalid credentials")

    token, expires_in = create_access_token(subject="admin", username=username)
    return LoginTokenData(accessToken=token, expiresIn=expires_in)

