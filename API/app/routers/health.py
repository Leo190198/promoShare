from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import HealthData, SuccessEnvelope, success_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SuccessEnvelope[HealthData])
async def health() -> dict:
    return success_response(HealthData())

