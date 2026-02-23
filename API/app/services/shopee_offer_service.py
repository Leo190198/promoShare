from __future__ import annotations

import re
from typing import Any

from app.constants.graphql_queries import SELECTION_SET_VERSION
from app.core.cache import get_cache_manager
from app.core.exceptions import ApiException, UpstreamShopeeException
from app.schemas.shopee_offers import (
    ProductFromUrlData,
    ProductFromUrlRequest,
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


_SHOPEE_ITEM_PATTERNS = (
    re.compile(r"/(?:[^/?#]+-)?i\.(?P<shop_id>\d+)\.(?P<item_id>\d+)(?:[/?#]|$)", re.IGNORECASE),
    re.compile(r"/product/(?P<shop_id>\d+)/(?P<item_id>\d+)(?:[/?#]|$)", re.IGNORECASE),
)


def parse_shopee_product_url_ids(url: str) -> tuple[int, int]:
    for pattern in _SHOPEE_ITEM_PATTERNS:
        match = pattern.search(url)
        if match:
            return int(match.group("shop_id")), int(match.group("item_id"))
    raise ApiException(
        status_code=400,
        code="invalid_product_url",
        message="Could not extract shopId and itemId from Shopee product URL",
        details={"url": url},
    )


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


async def get_product_post_data_from_url(payload: ProductFromUrlRequest) -> tuple[ProductFromUrlData, bool]:
    shop_id, item_id = parse_shopee_product_url_ids(str(payload.url))
    search_payload = ProductOffersSearchRequest(itemId=item_id, page=1, limit=1)
    data, cached = await search_product_offers(search_payload)

    if not data.nodes:
        raise ApiException(
            status_code=404,
            code="product_not_found",
            message="Product was not found in Shopee productOfferV2 results",
            details={"shopId": shop_id, "itemId": item_id},
        )

    node = data.nodes[0]
    if node.itemId != item_id:
        raise ApiException(
            status_code=502,
            code="unexpected_product_mismatch",
            message="Shopee returned a different product than requested",
            details={"expectedItemId": item_id, "returnedItemId": node.itemId},
        )

    # If shopId is present in response, keep it authoritative; otherwise fall back to parsed URL.
    resolved_shop_id = node.shopId if node.shopId is not None else shop_id
    return (
        ProductFromUrlData(
            shopId=resolved_shop_id,
            itemId=item_id,
            productName=node.productName,
            imageUrl=node.imageUrl,
            priceMin=node.priceMin,
            priceMax=node.priceMax,
            offerLink=node.offerLink,
            productLink=node.productLink,
            shopName=node.shopName,
            commissionRate=node.commissionRate,
        ),
        cached,
    )
