import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.integrations.oauth_types import OAuthUserInfo
from app.main import app


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str, shop_name: str = "My Shop") -> dict[str, str]:
    return {
        "name": "Order Tester",
        "shopName": shop_name,
        "email": email,
        "password": "secret123",
    }


async def _registered_client() -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    return client


async def _create_order(client: AsyncClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "customerName": "Rahim Uddin",
        "customerPhone": "01711-223344",
        "address": "Mirpur, Dhaka",
        "items": [{"productName": "Cotton Panjabi - Maroon", "quantity": 1, "price": 1450}],
    }
    payload.update(overrides)
    response = await client.post("/api/v1/orders", json=payload)
    data: dict[str, object] = response.json()["data"]
    return data


async def test_list_orders_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/orders")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "NOT_AUTHENTICATED"


async def test_list_orders_is_empty_for_new_shop(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get("/api/v1/orders")

    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_create_order_uses_sensible_defaults(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/orders",
        json={
            "customerName": "Rahim Uddin",
            "customerPhone": "01711-223344",
            "address": "Mirpur, Dhaka",
            "items": [{"productName": "Cotton Panjabi - Maroon", "quantity": 1, "price": 1450}],
        },
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["orderNumber"] == "1001"
    assert body["channel"] == "manual"
    assert body["status"] == "pending"
    assert body["paymentMethod"] == "cod"
    assert body["isHighRisk"] is False
    assert body["tags"] == []
    assert body["notes"] == []
    assert len(body["items"]) == 1
    assert body["items"][0]["productName"] == "Cotton Panjabi - Maroon"
    assert "createdAt" in body


async def test_create_order_with_explicit_fields(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/orders",
        json={
            "customerName": "Mitu Rahman",
            "customerPhone": "01822-556677",
            "address": "Gulshan, Dhaka",
            "channel": "messenger",
            "paymentMethod": "prepaid",
            "courier": "pathao",
            "isHighRisk": True,
            "tags": ["VIP", "VIP", "  ", "repeat-customer"],
            "items": [
                {"productName": "Leather Handbag", "quantity": 1, "price": 2250},
                {"productName": "Scarf", "quantity": 2, "price": 350},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["channel"] == "messenger"
    assert body["paymentMethod"] == "prepaid"
    assert body["courier"] == "pathao"
    assert body["isHighRisk"] is True
    assert body["tags"] == ["VIP", "repeat-customer"]
    assert len(body["items"]) == 2


async def test_create_order_rejects_blank_customer_name(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/orders",
        json={
            "customerName": "   ",
            "customerPhone": "01711-223344",
            "address": "Mirpur, Dhaka",
            "items": [{"productName": "Cotton Panjabi", "quantity": 1, "price": 1450}],
        },
    )

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_create_order_rejects_empty_items(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/orders",
        json={
            "customerName": "Rahim Uddin",
            "customerPhone": "01711-223344",
            "address": "Mirpur, Dhaka",
            "items": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_second_order_gets_sequential_order_number(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    first = await _create_order(client)
    second = await _create_order(client)

    assert first["orderNumber"] == "1001"
    assert second["orderNumber"] == "1002"


async def test_get_order_returns_detail(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    response = await client.get(f"/api/v1/orders/{order['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == order["id"]


async def test_get_unknown_order_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get(f"/api/v1/orders/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "ORDER_NOT_FOUND"


async def test_update_order_changes_core_fields_and_items(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    response = await client.patch(
        f"/api/v1/orders/{order['id']}",
        json={
            "customerName": "Rahim U.",
            "customerPhone": "01700-000000",
            "address": "Dhanmondi, Dhaka",
            "channel": "instagram",
            "paymentMethod": "prepaid",
            "courier": "redx",
            "isHighRisk": True,
            "items": [{"productName": "T-Shirt - XL", "quantity": 3, "price": 450}],
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["customerName"] == "Rahim U."
    assert body["address"] == "Dhanmondi, Dhaka"
    assert body["paymentMethod"] == "prepaid"
    assert body["courier"] == "redx"
    assert body["isHighRisk"] is True
    assert len(body["items"]) == 1
    assert body["items"][0]["productName"] == "T-Shirt - XL"


async def test_update_unknown_order_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.patch(
        f"/api/v1/orders/{uuid.uuid4()}",
        json={
            "customerName": "X",
            "customerPhone": "01700-000000",
            "address": "Dhaka",
            "channel": "manual",
            "paymentMethod": "cod",
            "items": [{"productName": "Item", "quantity": 1, "price": 100}],
        },
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "ORDER_NOT_FOUND"


async def test_update_order_status(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    response = await client.patch(
        f"/api/v1/orders/{order['id']}/status", json={"status": "shipped"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "shipped"


async def test_update_status_on_unknown_order_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.patch(
        f"/api/v1/orders/{uuid.uuid4()}/status", json={"status": "cancelled"}
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "ORDER_NOT_FOUND"


async def test_replace_order_tags(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client, tags=["old-tag"])

    response = await client.put(f"/api/v1/orders/{order['id']}/tags", json={"tags": ["new-tag"]})

    assert response.status_code == 200
    assert response.json()["data"]["tags"] == ["new-tag"]


async def test_add_note_to_order(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    response = await client.post(
        f"/api/v1/orders/{order['id']}/notes", json={"text": "Customer confirmed via call."}
    )

    assert response.status_code == 201
    notes = response.json()["data"]["notes"]
    assert len(notes) == 1
    assert notes[0]["text"] == "Customer confirmed via call."

    second_response = await client.post(
        f"/api/v1/orders/{order['id']}/notes", json={"text": "Handed to courier."}
    )
    assert len(second_response.json()["data"]["notes"]) == 2


async def test_add_note_rejects_blank_text(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    response = await client.post(f"/api/v1/orders/{order['id']}/notes", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_delete_order_removes_it(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    delete_response = await client.delete(f"/api/v1/orders/{order['id']}")
    list_response = await client.get("/api/v1/orders")

    assert delete_response.status_code == 200
    assert list_response.json()["data"] == []


async def test_delete_unknown_order_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.delete(f"/api/v1/orders/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "ORDER_NOT_FOUND"


async def test_orders_are_isolated_between_shops(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    order = await _create_order(client)

    other_client = await _registered_client()
    try:
        list_response = await other_client.get("/api/v1/orders")
        get_response = await other_client.get(f"/api/v1/orders/{order['id']}")
        status_response = await other_client.patch(
            f"/api/v1/orders/{order['id']}/status", json={"status": "cancelled"}
        )
        delete_response = await other_client.delete(f"/api/v1/orders/{order['id']}")
    finally:
        await other_client.aclose()

    assert list_response.json()["data"] == []
    assert get_response.status_code == 404
    assert status_response.status_code == 404
    assert delete_response.status_code == 404


async def test_oauth_user_without_shop_sees_empty_list_and_cannot_create_order(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()

    async def fake_exchange(code: str) -> OAuthUserInfo:
        return OAuthUserInfo(email=email, name="No Shop User", provider_user_id="google-order-1")

    monkeypatch.setattr("app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange)
    client.cookies.set("oauth_state", "order-state")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "order-code", "state": "order-state"},
        follow_redirects=False,
    )

    list_response = await client.get("/api/v1/orders")
    create_response = await client.post(
        "/api/v1/orders",
        json={
            "customerName": "Nope",
            "customerPhone": "0000",
            "address": "Nowhere",
            "items": [{"productName": "Item", "quantity": 1, "price": 100}],
        },
    )

    assert list_response.status_code == 200
    assert list_response.json()["data"] == []
    assert create_response.status_code == 400
    assert create_response.json()["errorCode"] == "SHOP_REQUIRED"
