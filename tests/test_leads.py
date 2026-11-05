import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.integrations.oauth_types import OAuthUserInfo
from app.main import app


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str, shop_name: str = "My Shop") -> dict[str, str]:
    return {
        "name": "Lead Tester",
        "shopName": shop_name,
        "email": email,
        "password": "secret123",
    }


async def _registered_client() -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    return client


async def _create_lead(client: AsyncClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"name": "Tanvir Ahmed", "phone": "01711-223344"}
    payload.update(overrides)
    response = await client.post("/api/v1/leads", json=payload)
    data: dict[str, object] = response.json()["data"]
    return data


async def test_list_leads_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/leads")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "NOT_AUTHENTICATED"


async def test_list_leads_is_empty_for_new_shop(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get("/api/v1/leads")

    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_create_lead_uses_sensible_defaults(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/leads", json={"name": "Tanvir Ahmed", "phone": "01711-223344"}
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["name"] == "Tanvir Ahmed"
    assert body["phone"] == "01711-223344"
    assert body["source"] == "Manual"
    assert body["stage"] == "new"
    assert body["tags"] == []
    assert body["notes"] == []
    assert "lastActivityAt" in body


async def test_create_lead_with_explicit_fields(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post(
        "/api/v1/leads",
        json={
            "name": "Mitu Rahman",
            "phone": "01822-556677",
            "source": "Messenger",
            "stage": "contacted",
            "tags": ["VIP", "VIP", "  ", "price-asked"],
        },
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["source"] == "Messenger"
    assert body["stage"] == "contacted"
    assert body["tags"] == ["VIP", "price-asked"]


async def test_create_lead_rejects_blank_name(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.post("/api/v1/leads", json={"name": "   ", "phone": "01711-223344"})

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_get_lead_returns_detail(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    response = await client.get(f"/api/v1/leads/{lead['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == lead["id"]


async def test_get_unknown_lead_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.get(f"/api/v1/leads/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "LEAD_NOT_FOUND"


async def test_update_lead_changes_core_fields(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    response = await client.patch(
        f"/api/v1/leads/{lead['id']}",
        json={"name": "Tanvir A.", "phone": "01700-000000", "source": "Instagram"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "Tanvir A."
    assert body["phone"] == "01700-000000"
    assert body["source"] == "Instagram"


async def test_update_unknown_lead_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.patch(
        f"/api/v1/leads/{uuid.uuid4()}",
        json={"name": "X", "phone": "01700-000000", "source": "Instagram"},
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "LEAD_NOT_FOUND"


async def test_update_lead_stage(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    response = await client.patch(
        f"/api/v1/leads/{lead['id']}/stage", json={"stage": "order_confirmed"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["stage"] == "order_confirmed"


async def test_update_stage_on_unknown_lead_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.patch(
        f"/api/v1/leads/{uuid.uuid4()}/stage", json={"stage": "lost"}
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "LEAD_NOT_FOUND"


async def test_replace_lead_tags(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client, tags=["old-tag"])

    response = await client.put(f"/api/v1/leads/{lead['id']}/tags", json={"tags": ["new-tag"]})

    assert response.status_code == 200
    assert response.json()["data"]["tags"] == ["new-tag"]


async def test_add_note_to_lead(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    response = await client.post(
        f"/api/v1/leads/{lead['id']}/notes", json={"text": "Called, will order next week."}
    )

    assert response.status_code == 201
    notes = response.json()["data"]["notes"]
    assert len(notes) == 1
    assert notes[0]["text"] == "Called, will order next week."

    second_response = await client.post(
        f"/api/v1/leads/{lead['id']}/notes", json={"text": "Confirmed color and size."}
    )
    assert len(second_response.json()["data"]["notes"]) == 2


async def test_add_note_rejects_blank_text(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    response = await client.post(f"/api/v1/leads/{lead['id']}/notes", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_delete_lead_removes_it(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    delete_response = await client.delete(f"/api/v1/leads/{lead['id']}")
    list_response = await client.get("/api/v1/leads")

    assert delete_response.status_code == 200
    assert list_response.json()["data"] == []


async def test_delete_unknown_lead_returns_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))

    response = await client.delete(f"/api/v1/leads/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "LEAD_NOT_FOUND"


async def test_leads_are_isolated_between_shops(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_register_payload(_unique_email()))
    lead = await _create_lead(client)

    other_client = await _registered_client()
    try:
        list_response = await other_client.get("/api/v1/leads")
        get_response = await other_client.get(f"/api/v1/leads/{lead['id']}")
        stage_response = await other_client.patch(
            f"/api/v1/leads/{lead['id']}/stage", json={"stage": "lost"}
        )
        delete_response = await other_client.delete(f"/api/v1/leads/{lead['id']}")
    finally:
        await other_client.aclose()

    assert list_response.json()["data"] == []
    assert get_response.status_code == 404
    assert stage_response.status_code == 404
    assert delete_response.status_code == 404


async def test_oauth_user_without_shop_sees_empty_list_and_cannot_create_lead(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()

    async def fake_exchange(code: str) -> OAuthUserInfo:
        return OAuthUserInfo(email=email, name="No Shop User", provider_user_id="google-lead-1")

    monkeypatch.setattr("app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange)
    client.cookies.set("oauth_state", "lead-state")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "lead-code", "state": "lead-state"},
        follow_redirects=False,
    )

    list_response = await client.get("/api/v1/leads")
    create_response = await client.post(
        "/api/v1/leads", json={"name": "Nope", "phone": "0000"}
    )

    assert list_response.status_code == 200
    assert list_response.json()["data"] == []
    assert create_response.status_code == 400
    assert create_response.json()["errorCode"] == "SHOP_REQUIRED"
