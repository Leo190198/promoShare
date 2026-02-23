from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient


def test_product_offer_validation_requires_list_type_for_match_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/shopee/offers/products/search",
        headers=auth_headers,
        json={"matchId": 10012},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_product_offer_validation_list_mode_conflicts_with_keyword(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/shopee/offers/products/search",
        headers=auth_headers,
        json={"listType": 3, "matchId": 10012, "keyword": "demo"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


@respx.mock
def test_product_offer_success_and_cache_hit(client: TestClient, auth_headers: dict[str, str]) -> None:
    captured_queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_queries.append(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": 17979995178,
                                "productName": "Produto Demo",
                                "offerLink": "https://shope.ee/demo",
                                "productLink": "https://shopee.com.br/product/demo",
                            }
                        ],
                        "pageInfo": {"limit": 20, "hasNextPage": False, "scrollId": None},
                    }
                }
            },
        )

    route = respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(side_effect=handler)

    request_json = {"keyword": "shampoo", "page": 1, "limit": 20, "sortType": 2}
    first = client.post("/api/v1/shopee/offers/products/search", headers=auth_headers, json=request_json)
    second = client.post("/api/v1/shopee/offers/products/search", headers=auth_headers, json=request_json)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["meta"]["cached"] is False
    assert second.json()["meta"]["cached"] is True
    assert len(route.calls) == 1
    assert "productOfferV2" in captured_queries[0]
    assert 'keyword:\\"shampoo\\"' in captured_queries[0]


@respx.mock
def test_product_offer_maps_rate_limit_to_429(client: TestClient, auth_headers: dict[str, str]) -> None:
    respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "errors": [
                    {
                        "message": "error [10030]: too many requests",
                        "extensions": {"code": 10030, "message": "rate limit exceeded"},
                    }
                ]
            },
        )
    )

    response = client.post(
        "/api/v1/shopee/offers/products/search",
        headers=auth_headers,
        json={"keyword": "perfume"},
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "shopee_rate_limited"
