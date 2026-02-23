from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginTokenData(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    expiresIn: int


class MeData(BaseModel):
    username: str
    sub: str
    exp: int
    iat: int

