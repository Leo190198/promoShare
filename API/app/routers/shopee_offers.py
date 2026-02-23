from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.common import SuccessEnvelope, success_response
from app.schemas.shopee_offers import (
    ProductFromUrlData,
    ProductFromUrlRequest,
    ProductOfferSearchData,
    ProductOffersSearchRequest,
    ShopOfferSearchData,
    ShopOffersSearchRequest,
)
from app.services.shopee_offer_service import (
    get_product_post_data_from_url,
    search_product_offers,
    search_shop_offers,
)

router = APIRouter(prefix="/shopee/offers", tags=["shopee-offers"])


@router.post("/products/search", response_model=SuccessEnvelope[ProductOfferSearchData])
async def product_offers_search(
    payload: ProductOffersSearchRequest,
    _: dict = Depends(get_current_user),
) -> dict:
    data, cached = await search_product_offers(payload)
    return success_response(data, meta={"operation": "productOfferV2", "cached": cached})


@router.post("/products/from-url", response_model=SuccessEnvelope[ProductFromUrlData])
async def product_offers_from_url(
    payload: ProductFromUrlRequest,
    _: dict = Depends(get_current_user),
) -> dict:
    data, cached = await get_product_post_data_from_url(payload)
    return success_response(data, meta={"operation": "productFromUrl", "cached": cached})


@router.post("/shops/search", response_model=SuccessEnvelope[ShopOfferSearchData])
async def shop_offers_search(
    payload: ShopOffersSearchRequest,
    _: dict = Depends(get_current_user),
) -> dict:
    data, cached = await search_shop_offers(payload)
    return success_response(data, meta={"operation": "shopOfferV2", "cached": cached})
