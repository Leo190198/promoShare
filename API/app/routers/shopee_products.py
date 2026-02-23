from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.common import SuccessEnvelope, success_response
from app.schemas.shopee_offers import ProductFromUrlData, ProductFromUrlRequest
from app.services.shopee_offer_service import get_product_post_data_from_url

router = APIRouter(prefix="/shopee/products", tags=["shopee-products"])


@router.post("/from-url", response_model=SuccessEnvelope[ProductFromUrlData])
async def product_from_url(
    payload: ProductFromUrlRequest,
    _: dict = Depends(get_current_user),
) -> dict:
    data, cached = await get_product_post_data_from_url(payload)
    return success_response(data, meta={"operation": "productFromUrl", "cached": cached})

