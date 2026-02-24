from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorBody


class SuccessEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: dict[str, Any] | None = None


class HealthData(BaseModel):
    status: str = "ok"
    service: str = "promoshare-automation-api"


def success_response(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"success": True, "data": jsonable_encoder(data, exclude_none=True)}
    if meta is not None:
        payload["meta"] = jsonable_encoder(meta, exclude_none=True)
    return payload


def error_response(*, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"success": False, "error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = jsonable_encoder(details, exclude_none=True)
    return payload

