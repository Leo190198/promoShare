from __future__ import annotations

import os
import re

import httpx
import respx
from fastapi.testclient import TestClient

from app.services.shopee_signing import build_shopee_signature


def _parse_auth_header(header_value: str) -> tuple[int, str]:
    match = re.search(r"Timestamp=(\d+), Signature=([0-9a-f]{64})", header_value)
    assert match, header_value
    return int(match.group(1)), match.group(2)


def test_short_link_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/shopee/short-links",
        json={"originUrl": "https://shopee.com.br/produto-x"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@respx.mock
def test_short_link_success_builds_mutation_and_signature(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, json={"data": {"generateShortLink": {"shortLink": "https://shope.ee/abc123"}}})

    route = respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(side_effect=handler)

    response = client.post(
        "/api/v1/shopee/short-links",
        headers=auth_headers,
        json={
            "originUrl": "https://shopee.com.br/Apple-Iphone-11-128GB-Local-Set-i.52377417.6309028319",
            "subIds": ["s1", "s2"],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["shortLink"] == "https://shope.ee/abc123"
    assert payload["meta"] == {"operation": "generateShortLink", "cached": False}
    assert route.called
    assert "generateShortLink" in captured["body"]
    assert "originUrl" in captured["body"]

    timestamp, signature = _parse_auth_header(captured["auth"])
    expected = build_shopee_signature(
        app_id=os.environ["SHOPEE_APP_ID"],
        app_secret=os.environ["SHOPEE_APP_SECRET"],
        payload_json=captured["body"],
        timestamp=timestamp,
    )
    assert signature == expected.signature


@respx.mock
def test_short_link_maps_shopee_auth_error_to_502(client: TestClient, auth_headers: dict[str, str]) -> None:
    respx.post("https://open-api.affiliate.shopee.com.br/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "errors": [
                    {
                        "message": "error [10020]: Invalid Authorization Header",
                        "extensions": {"code": 10020, "message": "Invalid Authorization Header"},
                    }
                ]
            },
        )
    )

    response = client.post(
        "/api/v1/shopee/short-links",
        headers=auth_headers,
        json={"originUrl": "https://shopee.com.br/produto"},
    )
    assert response.status_code == 502
    payload = response.json()
    assert payload["error"]["code"] == "shopee_auth_error"
    assert payload["error"]["upstream"]["code"] == 10020

