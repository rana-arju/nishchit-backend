import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.cookies import (
    OAUTH_STATE_COOKIE,
    clear_oauth_state_cookie,
    set_auth_cookies,
    set_oauth_state_cookie,
)
from app.core.exceptions import AppException
from app.integrations import facebook_oauth, google_oauth
from app.models.enums import AuthProvider
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _login_redirect_with_error(error_code: str) -> RedirectResponse:
    settings = get_settings()
    query = urlencode({"error": error_code})
    response = RedirectResponse(
        f"{settings.frontend_url}/login?{query}", status_code=status.HTTP_302_FOUND
    )
    clear_oauth_state_cookie(response)
    return response


def _success_redirect(result: auth_service.AuthResult) -> RedirectResponse:
    settings = get_settings()
    destination = "/dashboard" if result.user.shop is not None else "/onboarding"
    response = RedirectResponse(
        f"{settings.frontend_url}{destination}", status_code=status.HTTP_302_FOUND
    )
    set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
    )
    clear_oauth_state_cookie(response)
    return response


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    authorization_url = google_oauth.build_authorization_url(state)
    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    set_oauth_state_cookie(response, state=state)
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    session: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if error or not code:
        return _login_redirect_with_error("OAUTH_CANCELLED")

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state or not expected_state or state != expected_state:
        return _login_redirect_with_error("OAUTH_STATE_MISMATCH")

    try:
        info = await google_oauth.exchange_code_for_user_info(code)
        result = await auth_service.login_with_oauth(
            session, provider=AuthProvider.GOOGLE, info=info
        )
    except AppException as exc:
        return _login_redirect_with_error(exc.error_code)

    return _success_redirect(result)


@router.get("/facebook/login")
async def facebook_login() -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    authorization_url = facebook_oauth.build_authorization_url(state)
    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    set_oauth_state_cookie(response, state=state)
    return response


@router.get("/facebook/callback")
async def facebook_callback(
    request: Request,
    session: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if error or not code:
        return _login_redirect_with_error("OAUTH_CANCELLED")

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state or not expected_state or state != expected_state:
        return _login_redirect_with_error("OAUTH_STATE_MISMATCH")

    try:
        info = await facebook_oauth.exchange_code_for_user_info(code)
        result = await auth_service.login_with_oauth(
            session, provider=AuthProvider.FACEBOOK, info=info
        )
    except AppException as exc:
        return _login_redirect_with_error(exc.error_code)

    return _success_redirect(result)
