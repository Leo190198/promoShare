from __future__ import annotations

from app.core.exceptions import UpstreamShopeeException
from app.schemas.shopee_short_links import ShortLinkCreateRequest, ShortLinkData
from app.services.shopee_client import ShopeeClient
from app.services.shopee_graphql_builder import build_generate_short_link_mutation


async def generate_short_link(payload: ShortLinkCreateRequest) -> ShortLinkData:
    client = ShopeeClient()
    query = build_generate_short_link_mutation(origin_url=str(payload.originUrl), sub_ids=payload.subIds)
    data = await client.execute(query=query, operation="generateShortLink")

    result = data.get("generateShortLink")
    if not isinstance(result, dict) or not result.get("shortLink"):
        raise UpstreamShopeeException(
            status_code=502,
            code="shopee_invalid_response",
            message="Shopee generateShortLink returned invalid payload",
            upstream={"operation": "generateShortLink"},
        )
    return ShortLinkData.model_validate(result)

