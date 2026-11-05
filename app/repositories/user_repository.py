from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import AuthProvider
from app.models.user import User


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).options(selectinload(User.shop)).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).options(selectinload(User.shop)).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    name: str,
    email: str,
    password_hash: str | None,
    auth_provider: AuthProvider = AuthProvider.LOCAL,
) -> User:
    user = User(name=name, email=email, password_hash=password_hash, auth_provider=auth_provider)
    session.add(user)
    await session.flush()
    return user
