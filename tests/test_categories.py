import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.integrations.oauth_types import OAuthUserInfo
from app.main import app


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str, shop_name: str = "My Shop") -> dict[str, str]:
    return {
        "name": "Category Tester",
        "shopName": shop_name,
        "email": email,
        "password": "secret123",
    }


async def _registered_client() -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    return client


async def test_list_categories_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/categories")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "NOT_AUTHENTICATED"


async def test_list_categories_is_empty_for_new_shop(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get("/api/v1/categories")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


async def test_create_category_succeeds(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post("/api/v1/categories", json={"name": "টি-শার্ট"})

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["name"] == "টি-শার্ট"
    assert body["productCount"] == 0
    assert "id" in body
    assert "createdAt" in body


async def test_create_category_trims_whitespace(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post("/api/v1/categories", json={"name": "  Shoes  "})

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Shoes"


async def test_create_category_rejects_blank_name(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post("/api/v1/categories", json={"name": "   "})

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_create_category_rejects_duplicate_name_in_same_shop(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    await client.post("/api/v1/categories", json={"name": "Electronics"})

    response = await client.post("/api/v1/categories", json={"name": "Electronics"})

    assert response.status_code == 409
    assert response.json()["errorCode"] == "CATEGORY_ALREADY_EXISTS"


async def test_same_category_name_allowed_across_different_shops(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    first_response = await client.post("/api/v1/categories", json={"name": "Electronics"})

    other_client = await _registered_client()
    try:
        second_response = await other_client.post(
            "/api/v1/categories", json={"name": "Electronics"}
        )
    finally:
        await other_client.aclose()

    assert first_response.status_code == 201
    assert second_response.status_code == 201


async def test_category_product_count_reflects_real_products(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    create_response = await client.post("/api/v1/categories", json={"name": "Electronics"})
    category_id = create_response.json()["data"]["id"]
    assert create_response.json()["data"]["productCount"] == 0

    for name in ("Speaker", "Headphones"):
        await client.post(
            "/api/v1/products",
            json={
                "name": name,
                "description": "",
                "categoryId": category_id,
                "price": 500,
                "discountPrice": None,
                "imageUrl": None,
                "imagePublicId": None,
                "inStock": True,
            },
        )

    list_response = await client.get("/api/v1/categories")
    rename_response = await client.patch(
        f"/api/v1/categories/{category_id}", json={"name": "Electronics & Gadgets"}
    )

    assert list_response.json()["data"][0]["productCount"] == 2
    assert rename_response.json()["data"]["productCount"] == 2


async def test_update_category_renames_it(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    create_response = await client.post("/api/v1/categories", json={"name": "Old Name"})
    category_id = create_response.json()["data"]["id"]

    response = await client.patch(f"/api/v1/categories/{category_id}", json={"name": "New Name"})

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "New Name"

    list_response = await client.get("/api/v1/categories")
    assert [c["name"] for c in list_response.json()["data"]] == ["New Name"]


async def test_update_category_rejects_name_clash_with_another_category(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    await client.post("/api/v1/categories", json={"name": "Shoes"})
    create_response = await client.post("/api/v1/categories", json={"name": "Bags"})
    category_id = create_response.json()["data"]["id"]

    response = await client.patch(f"/api/v1/categories/{category_id}", json={"name": "Shoes"})

    assert response.status_code == 409
    assert response.json()["errorCode"] == "CATEGORY_ALREADY_EXISTS"


async def test_update_category_allows_renaming_to_its_own_current_name(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    create_response = await client.post("/api/v1/categories", json={"name": "Shoes"})
    category_id = create_response.json()["data"]["id"]

    response = await client.patch(f"/api/v1/categories/{category_id}", json={"name": "Shoes"})

    assert response.status_code == 200


async def test_update_unknown_category_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.patch(
        f"/api/v1/categories/{uuid.uuid4()}", json={"name": "Anything"}
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "CATEGORY_NOT_FOUND"


async def test_delete_category_removes_it(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    create_response = await client.post("/api/v1/categories", json={"name": "Temporary"})
    category_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(f"/api/v1/categories/{category_id}")
    list_response = await client.get("/api/v1/categories")

    assert delete_response.status_code == 200
    assert list_response.json()["data"] == []


async def test_delete_unknown_category_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.delete(f"/api/v1/categories/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "CATEGORY_NOT_FOUND"


async def test_categories_are_isolated_between_shops(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    create_response = await client.post("/api/v1/categories", json={"name": "Owner Only"})
    category_id = create_response.json()["data"]["id"]

    other_client = await _registered_client()
    try:
        list_response = await other_client.get("/api/v1/categories")
        update_response = await other_client.patch(
            f"/api/v1/categories/{category_id}", json={"name": "Hijacked"}
        )
        delete_response = await other_client.delete(f"/api/v1/categories/{category_id}")
    finally:
        await other_client.aclose()

    assert list_response.json()["data"] == []
    assert update_response.status_code == 404
    assert delete_response.status_code == 404


async def test_oauth_user_without_shop_sees_empty_list_and_cannot_create(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()

    async def fake_exchange(code: str) -> OAuthUserInfo:
        return OAuthUserInfo(email=email, name="No Shop User", provider_user_id="google-cat-1")

    monkeypatch.setattr("app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange)
    client.cookies.set("oauth_state", "cat-state")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "cat-code", "state": "cat-state"},
        follow_redirects=False,
    )

    list_response = await client.get("/api/v1/categories")
    create_response = await client.post("/api/v1/categories", json={"name": "Nope"})

    assert list_response.status_code == 200
    assert list_response.json()["data"] == []
    assert create_response.status_code == 400
    assert create_response.json()["errorCode"] == "SHOP_REQUIRED"
