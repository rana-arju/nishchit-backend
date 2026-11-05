from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import bcrypt
import jwt

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import Unauthorized

TokenType = Literal["access", "refresh"]

ACCESS_TOKEN_TYPE: TokenType = "access"
REFRESH_TOKEN_TYPE: TokenType = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(user_id: UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    return _create_token(
        user_id, ACCESS_TOKEN_TYPE, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: UUID) -> str:
    settings = get_settings()
    return _create_token(
        user_id, REFRESH_TOKEN_TYPE, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, *, expected_type: TokenType) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized(messages.TOKEN_EXPIRED, error_code="TOKEN_EXPIRED") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized(messages.INVALID_TOKEN, error_code="INVALID_TOKEN") from exc

    if payload.get("type") != expected_type:
        raise Unauthorized(messages.INVALID_TOKEN, error_code="INVALID_TOKEN")

    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise Unauthorized(messages.INVALID_TOKEN, error_code="INVALID_TOKEN") from exc
