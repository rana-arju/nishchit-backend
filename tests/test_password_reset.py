import uuid

import pytest
from httpx import AsyncClient

from app.services import password_reset_service


def _unique_email() -> str:
    return f"{uuid.uuid4()}@example.com"


def _register_payload(email: str) -> dict[str, str]:
    return {
        "name": "Reset Test",
        "shopName": "Reset Shop",
        "email": email,
        "password": "secret123",
    }


def _patch_otp(monkeypatch: pytest.MonkeyPatch, *values: str) -> None:
    sequence = iter(values)
    monkeypatch.setattr(
        "app.services.password_reset_service._generate_otp", lambda: next(sequence)
    )


async def test_forgot_password_is_generic_for_unknown_email(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/forgot-password", json={"email": _unique_email()})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] is None


async def test_verify_otp_fails_for_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/verify-otp", json={"email": _unique_email(), "otp": "123456"}
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_OTP"


async def test_verify_otp_fails_without_requesting_one(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": "123456"})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "OTP_EXPIRED"


async def test_full_reset_flow_with_correct_otp(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))
    _patch_otp(monkeypatch, "654321")

    forgot_response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    verify_response = await client.post(
        "/api/v1/auth/verify-otp", json={"email": email, "otp": "654321"}
    )
    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": "654321", "newPassword": "new-secret-456"},
    )

    assert forgot_response.status_code == 200
    assert verify_response.status_code == 200
    assert reset_response.status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    new_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "new-secret-456"}
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_verify_otp_fails_with_wrong_code(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))
    _patch_otp(monkeypatch, "111111")
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    response = await client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": "999999"})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_OTP"


async def test_otp_is_locked_after_too_many_wrong_attempts(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))
    _patch_otp(monkeypatch, "222222")
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    last_response = None
    for _ in range(6):
        last_response = await client.post(
            "/api/v1/auth/verify-otp", json={"email": email, "otp": "000000"}
        )

    assert last_response is not None
    assert last_response.status_code == 400
    assert last_response.json()["errorCode"] == "OTP_LOCKED"


async def test_reset_password_cannot_reuse_consumed_otp(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))
    _patch_otp(monkeypatch, "333333")
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    first = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": "333333", "newPassword": "first-new-pass"},
    )
    second = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": "333333", "newPassword": "second-new-pass"},
    )

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["errorCode"] == "OTP_EXPIRED"


async def test_resend_cooldown_keeps_first_otp_valid(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))
    _patch_otp(monkeypatch, "444444", "555555")

    await client.post("/api/v1/auth/forgot-password", json={"email": email})
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    first_still_valid = await client.post(
        "/api/v1/auth/verify-otp", json={"email": email, "otp": "444444"}
    )

    assert first_still_valid.status_code == 200


async def test_forgot_password_does_nothing_for_oauth_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()

    async def fake_exchange(code: str) -> object:
        from app.integrations.oauth_types import OAuthUserInfo

        return OAuthUserInfo(email=email, name="Google User", provider_user_id="google-1")

    monkeypatch.setattr("app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange)
    client.cookies.set("oauth_state", "state-x")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-x", "state": "state-x"},
        follow_redirects=False,
    )

    forgot_response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    verify_response = await client.post(
        "/api/v1/auth/verify-otp", json={"email": email, "otp": "123456"}
    )

    assert forgot_response.status_code == 200
    assert verify_response.status_code == 400
    assert verify_response.json()["errorCode"] == "OTP_EXPIRED"


async def test_change_password_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "whatever", "newPassword": "new-secret-123"},
    )

    assert response.status_code == 401
    assert response.json()["errorCode"] == "NOT_AUTHENTICATED"


async def test_change_password_succeeds_with_correct_current_password(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "secret123", "newPassword": "brand-new-pass"},
    )

    assert response.status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    new_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "brand-new-pass"}
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_change_password_fails_with_wrong_current_password(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "not-the-right-password", "newPassword": "brand-new-pass"},
    )

    assert response.status_code == 401
    assert response.json()["errorCode"] == "CURRENT_PASSWORD_INCORRECT"


async def test_change_password_rejected_for_oauth_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = _unique_email()

    async def fake_exchange(code: str) -> object:
        from app.integrations.oauth_types import OAuthUserInfo

        return OAuthUserInfo(email=email, name="Google User", provider_user_id="google-2")

    monkeypatch.setattr("app.integrations.google_oauth.exchange_code_for_user_info", fake_exchange)
    client.cookies.set("oauth_state", "state-y")
    await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-y", "state": "state-y"},
        follow_redirects=False,
    )

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "anything", "newPassword": "brand-new-pass"},
    )

    assert response.status_code == 409
    assert response.json()["errorCode"] == "NO_PASSWORD_SET"


def test_generate_otp_is_six_digits() -> None:
    for _ in range(50):
        otp = password_reset_service._generate_otp()  # noqa: SLF001
        assert len(otp) == 6
        assert otp.isdigit()
