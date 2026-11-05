from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop


async def create(session: AsyncSession, *, name: str, owner_id: UUID) -> Shop:
    shop = Shop(name=name, owner_id=owner_id)
    session.add(shop)
    await session.flush()
    return shop
