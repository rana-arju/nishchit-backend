from fastapi import Response

from app.core.config import get_settings

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

_AUTH_COOKIE_PATH = "/"


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    settings = get_settings()

    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=_AUTH_COOKIE_PATH,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=_AUTH_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()

    response.delete_cookie(
        ACCESS_TOKEN_COOKIE,
        domain=settings.cookie_domain,
        path=_AUTH_COOKIE_PATH,
    )
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE,
        domain=settings.cookie_domain,
        path=_AUTH_COOKIE_PATH,
    )
