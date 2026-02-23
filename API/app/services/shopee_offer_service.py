from __future__ import annotations

from typing import Any

from app.constants.graphql_queries import SELECTION_SET_VERSION
from app.core.cache import get_cache_manager
from app.core.exceptions import UpstreamShopeeException
from app.schemas.shopee_offers import (
    ProductOfferSearchData,
    ProductOffersSearchRequest,
    ShopOfferSearchData,
    ShopOffersSearchRequest,
)
from app.services.shopee_client import ShopeeClient
from app.services.shopee_graphql_builder import build_product_offer_v2_query, build_shop_offer_v2_query


def _validate_connection_payload(payload: Any, *, operation: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise UpstreamShopeeException(
            status_code=502,
            code="shopee_invalid_response",
            message=f"Shopee {operation} returned invalid payload",
            upstream={"operation": operation},
        )
    if not isinstance(payload.get("nodes"), list):
        raise UpstreamShopeeException(
            status_code=502,
            code="shopee_invalid_response",
            message=f"Shopee {operation} response missing nodes list",
            upstream={"operation": operation},
        )
    if not isinstance(payload.get("pageInfo"), dict):
        raise UpstreamShopeeException(
            status_code=502,
            code="shopee_invalid_response",
            message=f"Shopee {operation} response missing pageInfo object",
            upstream={"operation": operation},
        )
    return payload


async def search_product_offers(payload: ProductOffersSearchRequest) -> tuple[ProductOfferSearchData, bool]:
    cache = get_cache_manager()
    request_data = payload.model_dump(exclude_none=True)
    cache_key = cache.build_key("productOfferV2", request_data, SELECTION_SET_VERSION)

    cached = cache.get("product_offers", cache_key)
    if cached is not None:
        return ProductOfferSearchData.model_validate(cached), True

    client = ShopeeClient()
    query = build_product_offer_v2_query(request_data)
    data = await client.execute(query=query, operation="productOfferV2")

    connection = _validate_connection_payload(data.get("productOfferV2"), operation="productOfferV2")
    cache.set("product_offers", cache_key, connection)
    return ProductOfferSearchData.model_validate(connection), False


async def search_shop_offers(payload: ShopOffersSearchRequest) -> tuple[ShopOfferSearchData, bool]:
    cache = get_cache_manager()
    request_data = payload.model_dump(exclude_none=True)
    cache_key = cache.build_key("shopOfferV2", request_data, SELECTION_SET_VERSION)

    cached = cache.get("shop_offers", cache_key)
    if cached is not None:
        return ShopOfferSearchData.model_validate(cached), True

    client = ShopeeClient()
    query = build_shop_offer_v2_query(request_data)
    data = await client.execute(query=query, operation="shopOfferV2")

    connection = _validate_connection_payload(data.get("shopOfferV2"), operation="shopOfferV2")
    cache.set("shop_offers", cache_key, connection)
    return ShopOfferSearchData.model_validate(connection), False

