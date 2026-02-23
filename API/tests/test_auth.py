from __future__ import annotations

from fastapi.testclient import TestClient


def test_login_success_and_me(client: TestClient) -> None:
    login_response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass"})

    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["success"] is True
    assert payload["data"]["tokenType"] == "Bearer"
    assert payload["data"]["expiresIn"] == 86400
    assert payload["data"]["accessToken"]

    headers = {"Authorization": f"Bearer {payload['data']['accessToken']}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["data"]["username"] == "admin"
    assert me_payload["data"]["sub"] == "admin"
    assert isinstance(me_payload["data"]["exp"], int)
    assert isinstance(me_payload["data"]["iat"], int)


def test_login_invalid_credentials(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "invalid_credentials"


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"

