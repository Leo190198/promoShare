from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.auth import LoginRequest, LoginTokenData, MeData
from app.schemas.common import SuccessEnvelope, success_response
from app.services.auth_service import login_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SuccessEnvelope[LoginTokenData])
async def login(payload: LoginRequest) -> dict:
    data = login_user(username=payload.username, password=payload.password)
    return success_response(data)


@router.get("/me", response_model=SuccessEnvelope[MeData])
async def me(current_user: dict = Depends(get_current_user)) -> dict:
    data = MeData(
        username=str(current_user.get("username", "")),
        sub=str(current_user.get("sub", "")),
        exp=int(current_user.get("exp", 0)),
        iat=int(current_user.get("iat", 0)),
    )
    return success_response(data)

