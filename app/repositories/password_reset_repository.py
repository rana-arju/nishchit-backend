from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_otp import PasswordResetOtp


async def create(
    session: AsyncSession, *, user_id: UUID, otp_hash: str, expires_at: datetime
) -> PasswordResetOtp:
    otp = PasswordResetOtp(user_id=user_id, otp_hash=otp_hash, expires_at=expires_at)
    session.add(otp)
    await session.flush()
    return otp


async def get_latest_active(session: AsyncSession, user_id: UUID) -> PasswordResetOtp | None:
    stmt = (
        select(PasswordResetOtp)
        .where(PasswordResetOtp.user_id == user_id, PasswordResetOtp.consumed_at.is_(None))
        .order_by(PasswordResetOtp.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def increment_attempts(session: AsyncSession, otp: PasswordResetOtp) -> None:
    otp.attempt_count += 1
    await session.flush()


async def mark_consumed(
    session: AsyncSession, otp: PasswordResetOtp, *, consumed_at: datetime
) -> None:
    otp.consumed_at = consumed_at
    await session.flush()
