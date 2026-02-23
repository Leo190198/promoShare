from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.common import SuccessEnvelope, success_response
from app.schemas.shopee_short_links import ShortLinkCreateRequest, ShortLinkData
from app.services.shopee_short_link_service import generate_short_link

router = APIRouter(prefix="/shopee", tags=["shopee-short-links"])


@router.post("/short-links", response_model=SuccessEnvelope[ShortLinkData])
async def create_short_link(
    payload: ShortLinkCreateRequest,
    _: dict = Depends(get_current_user),
) -> dict:
    data = await generate_short_link(payload)
    return success_response(data, meta={"operation": "generateShortLink", "cached": False})
