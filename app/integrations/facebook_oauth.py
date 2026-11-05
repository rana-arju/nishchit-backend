from urllib.parse import urlencode

import httpx

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, ServiceUnavailable
from app.integrations.oauth_types import OAuthUserInfo

GRAPH_API_VERSION = "v19.0"
AUTHORIZATION_URL = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth"
TOKEN_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
USERINFO_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me"


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.facebook_client_id
        and settings.facebook_client_secret
        and settings.facebook_redirect_uri
    )


def build_authorization_url(state: str) -> str:
    settings = get_settings()
    if not settings.facebook_client_id or not settings.facebook_redirect_uri:
        raise ServiceUnavailable(
            messages.FACEBOOK_LOGIN_NOT_CONFIGURED, error_code="FACEBOOK_LOGIN_NOT_CONFIGURED"
        )

    params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "response_type": "code",
        "scope": "email,public_profile",
        "state": state,
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code_for_user_info(code: str) -> OAuthUserInfo:
    settings = get_settings()
    if (
        not settings.facebook_client_id
        or not settings.facebook_client_secret
        or not settings.facebook_redirect_uri
    ):
        raise ServiceUnavailable(
            messages.FACEBOOK_LOGIN_NOT_CONFIGURED, error_code="FACEBOOK_LOGIN_NOT_CONFIGURED"
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.get(
            TOKEN_URL,
            params={
                "code": code,
                "client_id": settings.facebook_client_id,
                "client_secret": settings.facebook_client_secret,
                "redirect_uri": settings.facebook_redirect_uri,
            },
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise ExternalServiceError(
                messages.OAUTH_EXCHANGE_FAILED, error_code="OAUTH_EXCHANGE_FAILED"
            )

        userinfo_response = await client.get(
            USERINFO_URL,
            params={"fields": "id,name,email", "access_token": access_token},
        )
        userinfo_response.raise_for_status()
        payload = userinfo_response.json()

    email = payload.get("email")
    if not email:
        raise ExternalServiceError(
            messages.OAUTH_EMAIL_NOT_PROVIDED, error_code="OAUTH_EMAIL_NOT_PROVIDED"
        )

    return OAuthUserInfo(
        email=email.strip().lower(),
        name=payload.get("name") or email,
        provider_user_id=str(payload["id"]),
    )
