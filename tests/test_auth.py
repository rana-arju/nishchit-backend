import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str) -> dict[str, str]:
    return {
        "name": "Rahim Uddin",
        "shopName": "Rahim's Fashion House",
        "email": email,
        "password": "secret123",
    }


async def test_register_creates_user_and_shop_and_sets_cookies(client: AsyncClient) -> None:
    email = _unique_email()

    response = await client.post("/api/v1/auth/register", json=_register_payload(email))

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == email
    assert body["data"]["name"] == "Rahim Uddin"
    assert body["data"]["shop"]["name"] == "Rahim's Fashion House"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post("/api/v1/auth/register", json=_register_payload(email))

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["errorCode"] == "EMAIL_ALREADY_REGISTERED"


async def test_register_rejects_invalid_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "", "shopName": "Shop", "email": "not-an-email", "password": "123"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["errorCode"] == "VALIDATION_ERROR"
    assert len(body["errorMessages"]) >= 1


async def test_login_succeeds_with_correct_credentials(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["email"] == email
    assert "access_token" in response.cookies


async def test_login_fails_with_wrong_password(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["errorCode"] == "INVALID_CREDENTIALS"


async def test_login_fails_for_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": _unique_email(), "password": "secret123"}
    )

    assert response.status_code == 401
    assert response.json()["errorCode"] == "INVALID_CREDENTIALS"


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "NOT_AUTHENTICATED"


async def test_me_returns_current_user_after_login(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["data"]["email"] == email


async def test_refresh_issues_new_access_token(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    refresh_response = await client.post("/api/v1/auth/refresh")
    me_response = await client.get("/api/v1/auth/me")

    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.cookies
    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == email


async def test_refresh_without_cookie_fails(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "MISSING_REFRESH_TOKEN"


async def test_logout_clears_session(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    logout_response = await client.post("/api/v1/auth/logout")
    me_response = await client.get("/api/v1/auth/me")

    assert logout_response.status_code == 200
    assert me_response.status_code == 401
