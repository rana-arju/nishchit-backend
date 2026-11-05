from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import BadRequest, Conflict, NotFound
from app.models.category import Category
from app.models.user import User
from app.repositories import category_repository


def _require_shop_id(user: User) -> UUID:
    if user.shop is None:
        raise BadRequest(messages.SHOP_REQUIRED, error_code="SHOP_REQUIRED")
    return user.shop.id


async def list_categories(session: AsyncSession, *, user: User) -> list[Category]:
    if user.shop is None:
        return []
    return await category_repository.list_by_shop(session, user.shop.id)


async def create_category(session: AsyncSession, *, user: User, name: str) -> Category:
    shop_id = _require_shop_id(user)

    existing = await category_repository.get_by_name(session, shop_id, name)
    if existing is not None:
        raise Conflict(messages.CATEGORY_ALREADY_EXISTS, error_code="CATEGORY_ALREADY_EXISTS")

    category = await category_repository.create(session, shop_id=shop_id, name=name)
    await session.commit()

    return category


async def update_category(
    session: AsyncSession, *, user: User, category_id: UUID, name: str
) -> Category:
    shop_id = _require_shop_id(user)

    category = await category_repository.get_by_id(session, category_id, shop_id)
    if category is None:
        raise NotFound(messages.CATEGORY_NOT_FOUND, error_code="CATEGORY_NOT_FOUND")

    if name != category.name:
        existing = await category_repository.get_by_name(session, shop_id, name)
        if existing is not None and existing.id != category.id:
            raise Conflict(messages.CATEGORY_ALREADY_EXISTS, error_code="CATEGORY_ALREADY_EXISTS")
        category.name = name
        await session.commit()

    return category


async def delete_category(session: AsyncSession, *, user: User, category_id: UUID) -> None:
    shop_id = _require_shop_id(user)

    category = await category_repository.get_by_id(session, category_id, shop_id)
    if category is None:
        raise NotFound(messages.CATEGORY_NOT_FOUND, error_code="CATEGORY_NOT_FOUND")

    await category_repository.delete(session, category)
    await session.commit()
