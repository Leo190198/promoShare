from __future__ import annotations

import threading
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ApiException


class ShopeeApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._token: str | None = None
        self._lock = threading.Lock()

    def _login(self) -> str:
        if not self.settings.shopee_api_username or not self.settings.shopee_api_password:
            raise ApiException(
                status_code=500,
                code="shopee_api_credentials_missing",
                message="Shopee API credentials are not configured in automation service",
            )

        url = self.settings.shopee_api_base_url.rstrip("/") + "/api/v1/auth/login"
        try:
            with httpx.Client(timeout=self.settings.shopee_api_timeout_seconds) as client:
                response = client.post(
                    url,
                    json={
                        "username": self.settings.shopee_api_username,
                        "password": self.settings.shopee_api_password,
                    },
                )
        except httpx.HTTPError as exc:
            raise ApiException(
                status_code=502,
                code="shopee_api_unreachable",
                message="Failed to reach PromoShare Shopee API",
                details={"reason": str(exc)},
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise ApiException(
                status_code=502,
                code="shopee_api_invalid_response",
                message="PromoShare Shopee API returned invalid JSON on login",
            ) from exc

        if response.status_code != 200 or not isinstance(body, dict) or not body.get("success"):
            raise ApiException(
                status_code=502,
                code="shopee_api_login_failed",
                message="PromoShare Shopee API login failed",
                details={"statusCode": response.status_code, "body": body},
            )

        token = body.get("data", {}).get("accessToken")
        if not isinstance(token, str) or not token:
            raise ApiException(status_code=502, code="shopee_api_login_failed", message="Shopee API login missing token")
        return token

    def _get_token(self) -> str:
        with self._lock:
            if self._token:
                return self._token
            self._token = self._login()
            return self._token

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None, retry_auth: bool = True) -> dict[str, Any]:
        token = self._get_token()
        url = self.settings.shopee_api_base_url.rstrip("/") + path
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=self.settings.shopee_api_timeout_seconds) as client:
                response = client.request(method, url, headers=headers, json=json_body)
        except httpx.HTTPError as exc:
            raise ApiException(
                status_code=502,
                code="shopee_api_unreachable",
                message="Failed to communicate with PromoShare Shopee API",
                details={"reason": str(exc), "path": path},
            ) from exc

        if response.status_code == 401 and retry_auth:
            with self._lock:
                self._token = None
            return self._request(method, path, json_body=json_body, retry_auth=False)

        try:
            body = response.json()
        except ValueError as exc:
            raise ApiException(
                status_code=502,
                code="shopee_api_invalid_response",
                message="PromoShare Shopee API returned invalid JSON",
                details={"path": path, "statusCode": response.status_code},
            ) from exc

        if response.status_code >= 400 or not isinstance(body, dict):
            raise ApiException(
                status_code=502,
                code="shopee_api_http_error",
                message="PromoShare Shopee API returned error",
                details={"path": path, "statusCode": response.status_code, "body": body},
            )

        if not body.get("success"):
            raise ApiException(
                status_code=502,
                code="shopee_api_error",
                message="PromoShare Shopee API operation failed",
                details={"path": path, "body": body},
            )
        return body

    def search_products(self, *, keyword: str, page: int = 1, limit: int = 10, sort_type: int = 2) -> list[dict[str, Any]]:
        body = self._request(
            "POST",
            "/api/v1/shopee/offers/products/search",
            json_body={"keyword": keyword, "page": page, "limit": limit, "sortType": sort_type},
        )
        nodes = body.get("data", {}).get("nodes", [])
        return nodes if isinstance(nodes, list) else []

    def generate_short_link(self, *, origin_url: str) -> str:
        body = self._request("POST", "/api/v1/shopee/short-links", json_body={"originUrl": origin_url})
        short_link = body.get("data", {}).get("shortLink")
        if not isinstance(short_link, str) or not short_link:
            raise ApiException(
                status_code=502,
                code="shopee_api_invalid_response",
                message="PromoShare Shopee API short-link response missing shortLink",
            )
        return short_link


class WhatsAppApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.wa_api_key:
            raise ApiException(status_code=500, code="wa_api_key_missing", message="WA_API_KEY is not configured")

        url = self.settings.wa_api_base_url.rstrip("/") + path
        headers = {"X-API-Key": self.settings.wa_api_key}
        try:
            with httpx.Client(timeout=self.settings.wa_api_timeout_seconds) as client:
                response = client.request(method, url, headers=headers, json=json_body)
        except httpx.HTTPError as exc:
            raise ApiException(
                status_code=502,
                code="wa_api_unreachable",
                message="Failed to communicate with WhatsApp API",
                details={"reason": str(exc), "path": path},
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise ApiException(
                status_code=502,
                code="wa_api_invalid_response",
                message="WhatsApp API returned invalid JSON",
                details={"path": path, "statusCode": response.status_code},
            ) from exc

        if response.status_code >= 400:
            error = body.get("error", {}) if isinstance(body, dict) else {}
            raise ApiException(
                status_code=response.status_code if response.status_code in (400, 401, 404, 409, 422) else 502,
                code=error.get("code", "wa_api_http_error"),
                message=error.get("message", "WhatsApp API returned error"),
                details={"path": path, "body": body},
            )

        if not isinstance(body, dict):
            raise ApiException(status_code=502, code="wa_api_invalid_response", message="Unexpected WhatsApp API payload")
        return body

    def get_session_status(self) -> dict[str, Any]:
        body = self._request("GET", "/api/v1/session/status")
        data = body.get("data")
        return data if isinstance(data, dict) else {}

    def send_text_message(self, *, chat_id: str, text: str) -> dict[str, Any]:
        body = self._request("POST", "/api/v1/messages/send", json_body={"chatId": chat_id, "text": text})
        data = body.get("data")
        return data if isinstance(data, dict) else {}

