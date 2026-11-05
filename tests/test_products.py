import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.integrations.oauth_types import OAuthUserInfo
from app.main import app


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str, shop_name: str = "My Shop") -> dict[str, str]:
    return {
        "name": "Product Tester",
        "shopName": shop_name,
        "email": email,
        "password": "secret123",
    }


async def _registered_client() -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    return client


async def _create_category(client: AsyncClient, name: str = "Electronics") -> str:
    response = await client.post("/api/v1/categories", json={"name": name})
    category_id: str = response.json()["data"]["id"]
    return category_id


def _product_payload(category_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Bluetooth Speaker",
        "description": "Portable speaker with 12-hour battery.",
        "categoryId": category_id,
        "price": 1800,
        "discountPrice": None,
        "imageUrl": None,
        "imagePublicId": None,
        "inStock": True,
    }
    payload.update(overrides)
    return payload


def _patch_cloudinary(
    monkeypatch: pytest.MonkeyPatch, *, uploads: list[tuple[str, str]] | None = None
) -> list[str]:
    deleted_public_ids: list[str] = []
    upload_sequence = iter(uploads or [("https://cdn.example.com/img.png", "nishchit/img-1")])

    async def fake_upload(content: bytes) -> tuple[str, str]:
        return next(upload_sequence)

    async def fake_delete(public_id: str) -> None:
        deleted_public_ids.append(public_id)

    monkeypatch.setattr("app.integrations.cloudinary_storage.upload_image", fake_upload)
    monkeypatch.setattr("app.integrations.cloudinary_storage.delete_image", fake_delete)
    return deleted_public_ids


async def test_list_products_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "NOT_AUTHENTICATED"


async def test_list_products_is_empty_for_new_shop(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get("/api/v1/products")

    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_create_product_requires_existing_category(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/products", json=_product_payload(str(uuid.uuid4()))
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "CATEGORY_NOT_FOUND"


async def test_create_product_succeeds(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)

    response = await client.post("/api/v1/products", json=_product_payload(category_id))

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["name"] == "Bluetooth Speaker"
    assert body["categoryId"] == category_id
    assert body["categoryName"] == "Electronics"
    assert body["price"] == 1800
    assert body["inStock"] is True


async def test_create_product_rejects_non_positive_price(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)

    response = await client.post(
        "/api/v1/products", json=_product_payload(category_id, price=0)
    )

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_create_product_rejects_discount_price_not_lower_than_price(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)

    response = await client.post(
        "/api/v1/products",
        json=_product_payload(category_id, price=1000, discountPrice=1000),
    )

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_get_product_returns_detail(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post("/api/v1/products", json=_product_payload(category_id))
    product_id = create_response.json()["data"]["id"]

    response = await client.get(f"/api/v1/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == product_id


async def test_get_unknown_product_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get(f"/api/v1/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "PRODUCT_NOT_FOUND"


async def test_update_product_changes_fields(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post("/api/v1/products", json=_product_payload(category_id))
    product_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/products/{product_id}",
        json=_product_payload(category_id, name="Updated Speaker", price=2000, inStock=False),
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "Updated Speaker"
    assert body["price"] == 2000
    assert body["inStock"] is False


async def test_update_unknown_product_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)

    response = await client.patch(
        f"/api/v1/products/{uuid.uuid4()}", json=_product_payload(category_id)
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "PRODUCT_NOT_FOUND"


async def test_delete_product_removes_it(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post("/api/v1/products", json=_product_payload(category_id))
    product_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(f"/api/v1/products/{product_id}")
    list_response = await client.get("/api/v1/products")

    assert delete_response.status_code == 200
    assert list_response.json()["data"] == []


async def test_delete_unknown_product_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.delete(f"/api/v1/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "PRODUCT_NOT_FOUND"


async def test_products_are_isolated_between_shops(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post("/api/v1/products", json=_product_payload(category_id))
    product_id = create_response.json()["data"]["id"]

    other_client = await _registered_client()
    try:
        other_category_id = await _create_category(other_client, "Other Category")
        list_response = await other_client.get("/api/v1/products")
        get_response = await other_client.get(f"/api/v1/products/{product_id}")
        update_response = await other_client.patch(
            f"/api/v1/products/{product_id}", json=_product_payload(other_category_id)
        )
        delete_response = await other_client.delete(f"/api/v1/products/{product_id}")
    finally:
        await other_client.aclose()

    assert list_response.json()["data"] == []
    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404


async def test_cannot_update_product_with_category_from_another_shop(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post("/api/v1/products", json=_product_payload(category_id))
    product_id = create_response.json()["data"]["id"]

    other_client = await _registered_client()
    try:
        foreign_category_id = await _create_category(other_client, "Foreign Category")
    finally:
        await other_client.aclose()

    response = await client.patch(
        f"/api/v1/products/{product_id}", json=_product_payload(foreign_category_id)
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "CATEGORY_NOT_FOUND"


async def test_deleting_category_with_products_is_blocked(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    await client.post("/api/v1/products", json=_product_payload(category_id))

    response = await client.delete(f"/api/v1/categories/{category_id}")

    assert response.status_code == 409


async def test_upload_image_without_configuration_returns_service_unavailable(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/products/upload-image",
        files={"file": ("photo.png", b"fake-image-bytes", "image/png")},
    )

    assert response.status_code == 503
    assert response.json()["errorCode"] == "IMAGE_UPLOAD_NOT_CONFIGURED"


async def test_upload_image_rejects_non_image_content_type(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_cloudinary(monkeypatch)
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/products/upload-image",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_IMAGE_TYPE"


async def test_upload_image_succeeds_with_mocked_cloudinary(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_cloudinary(
        monkeypatch, uploads=[("https://cdn.example.com/img-1.png", "nishchit/img-1")]
    )
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/products/upload-image",
        files={"file": ("photo.png", b"fake-image-bytes", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["imageUrl"] == "https://cdn.example.com/img-1.png"
    assert body["imagePublicId"] == "nishchit/img-1"


async def test_deleting_product_removes_its_cloudinary_image(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    deleted = _patch_cloudinary(monkeypatch)
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post(
        "/api/v1/products",
        json=_product_payload(
            category_id,
            imageUrl="https://cdn.example.com/img-1.png",
            imagePublicId="nishchit/img-1",
        ),
    )
    product_id = create_response.json()["data"]["id"]

    await client.delete(f"/api/v1/products/{product_id}")

    assert deleted == ["nishchit/img-1"]


async def test_replacing_product_image_deletes_the_old_one(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    deleted = _patch_cloudinary(monkeypatch)
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    category_id = await _create_category(client)
    create_response = await client.post(
        "/api/v1/products",
        json=_product_payload(
            category_id,
            imageUrl="https://cdn.example.com/old.png",
            imagePublicId="nishchit/old",
        ),
    )
    product_id = create_response.json()["data"]["id"]

    await client.patch(
        f"/api/v1/products/{product_id}",
        json=_product_payload(
            category_id,
            imageUrl="https://cdn.example.com/new.png",
            imagePublicId="nishchit/new",
        ),
    )

    assert deleted == ["nishchit/old"]


async def test_oauth_user_without_shop_sees_empty_list_and_cannot_create_product(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()

    async def fake_exchange(code: str) -> OAuthUserInfo:
        return OAuthUserInfo(email=email, name="No Shop User", provider_user_id="google-prod-1")

    monkeypatch.setattr("app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange)
    client.cookies.set("oauth_state", "prod-state")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "prod-code", "state": "prod-state"},
        follow_redirects=False,
    )

    list_response = await client.get("/api/v1/products")
    create_response = await client.post(
        "/api/v1/products", json=_product_payload(str(uuid.uuid4()))
    )

    assert list_response.status_code == 200
    assert list_response.json()["data"] == []
    assert create_response.status_code == 400
    assert create_response.json()["errorCode"] == "SHOP_REQUIRED"
