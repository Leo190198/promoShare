from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient


def test_shop_offer_validation_shop_type_values(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/shopee/offers/shops/search",
        headers=auth_headers,
        json={"shopType": [1, 9]},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


@respx.mock
def test_shop_offer_success_builds_shop_offer_v2_query(client: TestClient, auth_headers: dict[str, str]) -> None:
    captured_query = {"body": ""}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_query["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "data": {
                    "shopOfferV2": {
                        "nodes": [
                            {
                                "shopId": 84499012,
                                "shopName": "Loja Demo",
                                "offerLink": "https://shope.ee/shopdemo",
                                "originalLink": "https://shopee.com.br/shop/84499012",
                                "commissionRate": "0.12",
                            }
                        ],
                        "pageInfo": {"limit": 20, "hasNextPage": True, "scrollId": "abc"},
                    }
                }
            },
        )

    route = respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(side_effect=handler)

    response = client.post(
        "/api/v1/shopee/offers/shops/search",
        headers=auth_headers,
        json={"keyword": "ikea", "sortType": 2},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["meta"]["operation"] == "shopOfferV2"
    assert payload["meta"]["cached"] is False
    assert payload["data"]["nodes"][0]["shopName"] == "Loja Demo"
    assert route.called
    assert "shopOfferV2" in captured_query["body"]
    assert 'keyword:\\"ikea\\"' in captured_query["body"]
