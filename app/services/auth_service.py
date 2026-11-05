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
from app.models.user import User
from app.repositories import shop_repository, user_repository


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


async def register(
    session: AsyncSession, *, name: str, shop_name: str, email: str, password: str
) -> AuthResult:
    existing_user = await user_repository.get_by_email(session, email)
    if existing_user is not None:
        raise Conflict(messages.EMAIL_ALREADY_REGISTERED, error_code="EMAIL_ALREADY_REGISTERED")

    user = await user_repository.create(
        session, name=name, email=email, password_hash=hash_password(password)
    )
    shop = await shop_repository.create(session, name=shop_name, owner_id=user.id)
    user.shop = shop

    await session.commit()

    return AuthResult(user=user, tokens=_issue_tokens(user.id))


async def login(session: AsyncSession, *, email: str, password: str) -> AuthResult:
    user = await user_repository.get_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        raise Unauthorized(messages.INVALID_CREDENTIALS, error_code="INVALID_CREDENTIALS")

    return AuthResult(user=user, tokens=_issue_tokens(user.id))


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
