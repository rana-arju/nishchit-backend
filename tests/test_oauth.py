import uuid

import pytest
from httpx import AsyncClient

from app.integrations.oauth_types import OAuthUserInfo


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str) -> dict[str, str]:
    return {
        "name": "Local User",
        "shopName": "Local Shop",
        "email": email,
        "password": "secret123",
    }


def _patch_google_exchange(monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    async def fake_exchange(code: str) -> OAuthUserInfo:
        return OAuthUserInfo(email=email, name="Google User", provider_user_id=f"google-{code}")

    monkeypatch.setattr(
        "app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange
    )


async def test_google_login_requires_configuration(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/google/login")

    assert response.status_code == 503
    assert response.json()["errorCode"] == "GOOGLE_LOGIN_NOT_CONFIGURED"


async def test_facebook_login_requires_configuration(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/facebook/login")

    assert response.status_code == 503
    assert response.json()["errorCode"] == "FACEBOOK_LOGIN_NOT_CONFIGURED"


async def test_google_callback_rejects_state_mismatch(client: AsyncClient) -> None:
    client.cookies.set("oauth_state", "expected-state")

    response = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "irrelevant", "state": "wrong-state"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "error=OAUTH_STATE_MISMATCH" in response.headers["location"]


async def test_google_callback_redirects_on_denied_consent(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/google/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "error=OAUTH_CANCELLED" in response.headers["location"]


async def test_google_callback_creates_new_user_without_shop(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    _patch_google_exchange(monkeypatch, email)
    client.cookies.set("oauth_state", "matching-state")

    response = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-1", "state": "matching-state"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].endswith("/onboarding")
    assert "access_token" in response.cookies

    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == email
    assert me_response.json()["data"]["shop"] is None


async def test_google_registered_user_cannot_login_with_password(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    _patch_google_exchange(monkeypatch, email)
    client.cookies.set("oauth_state", "state-1")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-2", "state": "state-1"},
        follow_redirects=False,
    )

    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "whatever123"}
    )

    assert response.status_code == 409
    assert response.json()["errorCode"] == "WRONG_LOGIN_METHOD"


async def test_local_user_cannot_login_via_google_with_same_email(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    _patch_google_exchange(monkeypatch, email)
    client.cookies.set("oauth_state", "state-2")

    response = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-3", "state": "state-2"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "error=WRONG_LOGIN_METHOD" in response.headers["location"]


async def test_cannot_register_with_email_already_used_via_google(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    _patch_google_exchange(monkeypatch, email)
    client.cookies.set("oauth_state", "state-3")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-4", "state": "state-3"},
        follow_redirects=False,
    )

    response = await client.post("/api/v1/auth/register", json=_register_payload(email))

    assert response.status_code == 409
    assert response.json()["errorCode"] == "EMAIL_REGISTERED_VIA_OTHER_METHOD"


async def test_set_shop_for_oauth_user_without_shop(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    _patch_google_exchange(monkeypatch, email)
    client.cookies.set("oauth_state", "state-4")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-5", "state": "state-4"},
        follow_redirects=False,
    )

    response = await client.post("/api/v1/auth/shop", json={"shopName": "My New Shop"})

    assert response.status_code == 200
    assert response.json()["data"]["shop"]["name"] == "My New Shop"


async def test_set_shop_fails_if_already_has_shop(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post("/api/v1/auth/shop", json={"shopName": "Another Shop"})

    assert response.status_code == 409
    assert response.json()["errorCode"] == "SHOP_ALREADY_EXISTS"
