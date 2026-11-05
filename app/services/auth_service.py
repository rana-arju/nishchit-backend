from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import Conflict, Unauthorized
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.integrations.oauth_types import OAuthUserInfo
from app.models.enums import AuthProvider
from app.models.user import User
from app.repositories import shop_repository, user_repository

_PROVIDER_LABELS: dict[AuthProvider, str] = {
    AuthProvider.LOCAL: "email and password",
    AuthProvider.GOOGLE: "Google",
    AuthProvider.FACEBOOK: "Facebook",
}


def _provider_label(provider: AuthProvider) -> str:
    return _PROVIDER_LABELS[provider]


@dataclass(frozen=True, slots=True)
class AuthTokens:
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    tokens: AuthTokens


def _issue_tokens(user_id: UUID) -> AuthTokens:
    return AuthTokens(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def _raise_for_provider_mismatch(existing_user: User, *, attempted: AuthProvider) -> None:
    if existing_user.auth_provider == attempted:
        return
    label = _provider_label(existing_user.auth_provider)
    raise Conflict(
        messages.WRONG_LOGIN_METHOD.format(provider=label),
        error_code="WRONG_LOGIN_METHOD",
    )


async def register(
    session: AsyncSession, *, name: str, shop_name: str, email: str, password: str
) -> AuthResult:
    existing_user = await user_repository.get_by_email(session, email)
    if existing_user is not None:
        if existing_user.auth_provider != AuthProvider.LOCAL:
            label = _provider_label(existing_user.auth_provider)
            raise Conflict(
                messages.EMAIL_REGISTERED_VIA_OTHER_METHOD.format(provider=label),
                error_code="EMAIL_REGISTERED_VIA_OTHER_METHOD",
            )
        raise Conflict(messages.EMAIL_ALREADY_REGISTERED, error_code="EMAIL_ALREADY_REGISTERED")

    user = await user_repository.create(
        session,
        name=name,
        email=email,
        password_hash=hash_password(password),
        auth_provider=AuthProvider.LOCAL,
    )
    shop = await shop_repository.create(session, name=shop_name, owner_id=user.id)
    user.shop = shop

    await session.commit()

    return AuthResult(user=user, tokens=_issue_tokens(user.id))


async def login(session: AsyncSession, *, email: str, password: str) -> AuthResult:
    user = await user_repository.get_by_email(session, email)
    if user is None:
        raise Unauthorized(messages.INVALID_CREDENTIALS, error_code="INVALID_CREDENTIALS")

    _raise_for_provider_mismatch(user, attempted=AuthProvider.LOCAL)

    if user.password_hash is None or not verify_password(password, user.password_hash):
        raise Unauthorized(messages.INVALID_CREDENTIALS, error_code="INVALID_CREDENTIALS")

    return AuthResult(user=user, tokens=_issue_tokens(user.id))


async def login_with_oauth(
    session: AsyncSession, *, provider: AuthProvider, info: OAuthUserInfo
) -> AuthResult:
    existing_user = await user_repository.get_by_email(session, info.email)
    if existing_user is not None:
        _raise_for_provider_mismatch(existing_user, attempted=provider)
        return AuthResult(user=existing_user, tokens=_issue_tokens(existing_user.id))

    user = await user_repository.create(
        session,
        name=info.name,
        email=info.email,
        password_hash=None,
        auth_provider=provider,
    )
    user.shop = None  # freshly created user has no shop; mark relationship as loaded
    await session.commit()

    return AuthResult(user=user, tokens=_issue_tokens(user.id))


async def set_shop(session: AsyncSession, *, user: User, shop_name: str) -> User:
    if user.shop is not None:
        raise Conflict(messages.SHOP_ALREADY_EXISTS, error_code="SHOP_ALREADY_EXISTS")

    shop = await shop_repository.create(session, name=shop_name, owner_id=user.id)
    user.shop = shop
    await session.commit()

    return user


async def refresh_access_token(session: AsyncSession, *, refresh_token: str) -> AuthTokens:
    user_id = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise Unauthorized(messages.INVALID_TOKEN, error_code="INVALID_TOKEN")

    return _issue_tokens(user.id)


async def get_current_user(session: AsyncSession, *, access_token: str) -> User:
    user_id = decode_token(access_token, expected_type=ACCESS_TOKEN_TYPE)
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise Unauthorized(messages.INVALID_TOKEN, error_code="INVALID_TOKEN")

    return user
