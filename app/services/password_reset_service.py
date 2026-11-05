import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import BadRequest
from app.core.security import hash_otp, hash_password, verify_otp_hash
from app.integrations.email_sender import send_email
from app.models.enums import AuthProvider
from app.models.password_reset_otp import PasswordResetOtp
from app.models.user import User
from app.repositories import password_reset_repository, user_repository


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def request_password_reset(session: AsyncSession, *, email: str) -> None:
    user = await user_repository.get_by_email(session, email)
    if user is None or user.auth_provider != AuthProvider.LOCAL:
        return

    settings = get_settings()
    existing = await password_reset_repository.get_latest_active(session, user.id)
    if existing is not None:
        cooldown = timedelta(seconds=settings.otp_resend_cooldown_seconds)
        if _utcnow() < existing.created_at + cooldown:
            return

    otp = _generate_otp()
    expires_at = _utcnow() + timedelta(minutes=settings.otp_expire_minutes)
    await password_reset_repository.create(
        session, user_id=user.id, otp_hash=hash_otp(otp), expires_at=expires_at
    )
    await session.commit()

    await send_email(
        to=user.email,
        subject="Your Nishchit password reset code",
        body=(
            f"Your password reset code is {otp}. "
            f"It expires in {settings.otp_expire_minutes} minutes."
        ),
    )


async def _get_valid_otp_or_raise(
    session: AsyncSession, *, email: str, otp: str
) -> tuple[User, PasswordResetOtp]:
    user = await user_repository.get_by_email(session, email)
    if user is None:
        raise BadRequest(messages.INVALID_OTP, error_code="INVALID_OTP")

    record = await password_reset_repository.get_latest_active(session, user.id)
    if record is None:
        raise BadRequest(messages.OTP_EXPIRED, error_code="OTP_EXPIRED")

    settings = get_settings()
    if record.attempt_count >= settings.otp_max_attempts:
        raise BadRequest(messages.OTP_LOCKED, error_code="OTP_LOCKED")

    if _utcnow() >= record.expires_at:
        raise BadRequest(messages.OTP_EXPIRED, error_code="OTP_EXPIRED")

    if not verify_otp_hash(otp, record.otp_hash):
        await password_reset_repository.increment_attempts(session, record)
        await session.commit()
        raise BadRequest(messages.INVALID_OTP, error_code="INVALID_OTP")

    return user, record


async def verify_otp(session: AsyncSession, *, email: str, otp: str) -> None:
    await _get_valid_otp_or_raise(session, email=email, otp=otp)


async def reset_password(
    session: AsyncSession, *, email: str, otp: str, new_password: str
) -> None:
    user, record = await _get_valid_otp_or_raise(session, email=email, otp=otp)

    user.password_hash = hash_password(new_password)
    await password_reset_repository.mark_consumed(session, record, consumed_at=_utcnow())
    await session.commit()
