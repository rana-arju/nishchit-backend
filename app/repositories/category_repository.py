from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def list_by_shop(session: AsyncSession, shop_id: UUID) -> list[Category]:
    stmt = (
        select(Category).where(Category.shop_id == shop_id).order_by(Category.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, category_id: UUID, shop_id: UUID) -> Category | None:
    stmt = select(Category).where(Category.id == category_id, Category.shop_id == shop_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_name(session: AsyncSession, shop_id: UUID, name: str) -> Category | None:
    stmt = select(Category).where(Category.shop_id == shop_id, Category.name == name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(session: AsyncSession, *, shop_id: UUID, name: str) -> Category:
    category = Category(shop_id=shop_id, name=name)
    session.add(category)
    await session.flush()
    return category


async def delete(session: AsyncSession, category: Category) -> None:
    await session.delete(category)
    await session.flush()
