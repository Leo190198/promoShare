from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from app.services.shopee_offer_service import parse_shopee_product_url_ids


def test_parse_shopee_product_url_ids_supports_slug_pattern() -> None:
    shop_id, item_id = parse_shopee_product_url_ids(
        "https://shopee.com.br/Apple-Mac-Mini-M4-i.560537952.58250067538?x=1"
    )
    assert shop_id == 560537952
    assert item_id == 58250067538


def test_parse_shopee_product_url_ids_supports_product_pattern() -> None:
    shop_id, item_id = parse_shopee_product_url_ids("https://shopee.com.br/product/560537952/58250067538")
    assert shop_id == 560537952
    assert item_id == 58250067538


def test_parse_shopee_product_url_ids_supports_opaanlp_pattern() -> None:
    shop_id, item_id = parse_shopee_product_url_ids("https://shopee.com.br/opaanlp/578878861/23297695767?__mobile__=1")
    assert shop_id == 578878861
    assert item_id == 23297695767


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


def test_product_from_url_validation_invalid_url(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/shopee/products/from-url",
        headers=auth_headers,
        json={"url": "https://google.com/produto/123"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_product_url"


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
def test_product_from_url_returns_post_ready_fields(client: TestClient, auth_headers: dict[str, str]) -> None:
    captured_queries: list[str] = []

    def graphql_handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        captured_queries.append(body)
        if "generateShortLink" in body:
            return httpx.Response(200, json={"data": {"generateShortLink": {"shortLink": "https://s.shopee.com.br/meu-short"}}})
        return httpx.Response(
            200,
            json={
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": 58250067538,
                                "shopId": 560537952,
                                "productName": "Apple Mac Mini M4",
                                "imageUrl": "https://cf.shopee.com.br/file/demo",
                                "priceMin": "4429",
                                "priceMax": "6999",
                                "offerLink": "https://s.shopee.com.br/demo",
                                "productLink": "https://shopee.com.br/product/560537952/58250067538",
                                "shopName": "Mundo Tech Imports_",
                                "commissionRate": "0.03",
                            }
                        ],
                        "pageInfo": {"limit": 1, "hasNextPage": False, "scrollId": None},
                    }
                }
            },
        )

    route = respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(side_effect=graphql_handler)

    response = client.post(
        "/api/v1/shopee/products/from-url",
        headers=auth_headers,
        json={"url": "https://shopee.com.br/Apple-Mac-Mini-M4-i.560537952.58250067538?x=1"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["itemId"] == 58250067538
    assert payload["data"]["shopId"] == 560537952
    assert payload["data"]["productName"] == "Apple Mac Mini M4"
    assert payload["data"]["imageUrl"] == "https://cf.shopee.com.br/file/demo"
    assert payload["data"]["offerLink"] == "https://s.shopee.com.br/demo"
    assert payload["data"]["shortLink"] == "https://s.shopee.com.br/meu-short"
    assert payload["meta"]["operation"] == "productFromUrl"
    assert len(route.calls) == 2
    assert any("productOfferV2" in q for q in captured_queries)
    assert any("generateShortLink" in q for q in captured_queries)


@respx.mock
def test_product_from_short_share_url_resolves_redirect_and_generates_short_link(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    short_url = "https://s.shopee.com.br/1Vty9Ij1Sa?share_channel_code=1"
    final_url = "https://shopee.com.br/opaanlp/578878861/23297695767?__mobile__=1"

    respx.get(short_url).mock(
        return_value=httpx.Response(301, headers={"Location": final_url})
    )
    respx.get(final_url).mock(return_value=httpx.Response(200, text="ok"))

    def graphql_handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        if "generateShortLink" in body:
            return httpx.Response(200, json={"data": {"generateShortLink": {"shortLink": "https://s.shopee.com.br/final-short"}}})
        return httpx.Response(
            200,
            json={
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": 23297695767,
                                "shopId": 578878861,
                                "productName": "Produto via app share",
                                "imageUrl": "https://cf.shopee.com.br/file/app-share",
                                "priceMin": "99",
                                "priceMax": "199",
                                "offerLink": "https://s.shopee.com.br/offer-from-search",
                                "productLink": "https://shopee.com.br/product/578878861/23297695767",
                                "shopName": "Loja Demo",
                                "commissionRate": "0.05",
                            }
                        ],
                        "pageInfo": {"limit": 1, "hasNextPage": False, "scrollId": None},
                    }
                }
            },
        )

    respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(side_effect=graphql_handler)

    response = client.post("/api/v1/shopee/products/from-url", headers=auth_headers, json={"url": short_url})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["shopId"] == 578878861
    assert payload["data"]["itemId"] == 23297695767
    assert payload["data"]["shortLink"] == "https://s.shopee.com.br/final-short"
    assert payload["data"]["productLink"] == "https://shopee.com.br/product/578878861/23297695767"


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
