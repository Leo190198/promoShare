from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamShopeeException
from app.services.shopee_graphql_builder import compact_json
from app.services.shopee_signing import build_shopee_signature


class ShopeeClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def execute(self, *, query: str, operation: str) -> dict[str, Any]:
        payload = {"query": query}
        payload_json = compact_json(payload)
        signature = build_shopee_signature(
            app_id=self.settings.shopee_app_id,
            app_secret=self.settings.shopee_app_secret,
            payload_json=payload_json,
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": signature.authorization_header,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.shopee_timeout_seconds) as client:
                response = await client.post(
                    self.settings.shopee_graphql_url,
                    content=payload_json.encode("utf-8"),
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise UpstreamShopeeException(
                status_code=502,
                code="shopee_network_error",
                message="Failed to communicate with Shopee API",
                upstream={"operation": operation, "reason": str(exc)},
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamShopeeException(
                status_code=502,
                code="shopee_invalid_response",
                message="Shopee API returned invalid JSON",
                upstream={"operation": operation, "httpStatus": response.status_code},
            ) from exc

        if response.status_code != 200:
            raise UpstreamShopeeException(
                status_code=502,
                code="shopee_http_error",
                message="Shopee API returned unexpected HTTP status",
                upstream={
                    "operation": operation,
                    "httpStatus": response.status_code,
                    "response": body if isinstance(body, dict) else {"raw": str(body)},
                },
            )

        if not isinstance(body, dict):
            raise UpstreamShopeeException(
                status_code=502,
                code="shopee_invalid_response",
                message="Shopee API returned unexpected payload type",
                upstream={"operation": operation},
            )

        errors = body.get("errors")
        if errors:
            first_error = errors[0] if isinstance(errors, list) and errors else {}
            message = first_error.get("message", "Shopee GraphQL error") if isinstance(first_error, dict) else str(first_error)
            extensions = first_error.get("extensions", {}) if isinstance(first_error, dict) else {}
            upstream_code = extensions.get("code") if isinstance(extensions, dict) else None
            upstream_message = extensions.get("message") if isinstance(extensions, dict) else None

            if upstream_code == 10030:
                raise UpstreamShopeeException(
                    status_code=429,
                    code="shopee_rate_limited",
                    message="Shopee API rate limit exceeded",
                    upstream={"operation": operation, "code": upstream_code, "message": upstream_message or message},
                )
            if upstream_code == 10020:
                raise UpstreamShopeeException(
                    status_code=502,
                    code="shopee_auth_error",
                    message="Shopee API authentication failed",
                    upstream={"operation": operation, "code": upstream_code, "message": upstream_message or message},
                )

            raise UpstreamShopeeException(
                status_code=502,
                code="shopee_upstream_error",
                message="Shopee API returned an error",
                upstream={"operation": operation, "code": upstream_code, "message": upstream_message or message},
            )

        data = body.get("data")
        if not isinstance(data, dict):
            raise UpstreamShopeeException(
                status_code=502,
                code="shopee_missing_data",
                message="Shopee API response missing data field",
                upstream={"operation": operation},
            )

        return data

