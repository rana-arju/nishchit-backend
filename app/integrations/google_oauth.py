from urllib.parse import urlencode

import httpx

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, ServiceUnavailable
from app.integrations.oauth_types import OAuthUserInfo

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri
    )


def build_authorization_url(state: str) -> str:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise ServiceUnavailable(
            messages.GOOGLE_LOGIN_NOT_CONFIGURED, error_code="GOOGLE_LOGIN_NOT_CONFIGURED"
        )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code_for_user_info(code: str) -> OAuthUserInfo:
    settings = get_settings()
    if (
        not settings.google_client_id
        or not settings.google_client_secret
        or not settings.google_redirect_uri
    ):
        raise ServiceUnavailable(
            messages.GOOGLE_LOGIN_NOT_CONFIGURED, error_code="GOOGLE_LOGIN_NOT_CONFIGURED"
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise ExternalServiceError(
                messages.OAUTH_EXCHANGE_FAILED, error_code="OAUTH_EXCHANGE_FAILED"
            )

        userinfo_response = await client.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo_response.raise_for_status()
        payload = userinfo_response.json()

    email = payload.get("email")
    if not email or not payload.get("email_verified"):
        raise ExternalServiceError(
            messages.OAUTH_EMAIL_NOT_PROVIDED, error_code="OAUTH_EMAIL_NOT_PROVIDED"
        )

    return OAuthUserInfo(
        email=email.strip().lower(),
        name=payload.get("name") or email,
        provider_user_id=str(payload["sub"]),
    )
