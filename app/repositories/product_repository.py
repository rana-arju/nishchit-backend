from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product


async def count_by_category(session: AsyncSession, shop_id: UUID) -> dict[UUID, int]:
    stmt = (
        select(Product.category_id, func.count(Product.id))
        .where(Product.shop_id == shop_id)
        .group_by(Product.category_id)
    )
    result = await session.execute(stmt)
    return dict(result.all())


async def list_by_shop(session: AsyncSession, shop_id: UUID) -> list[Product]:
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.shop_id == shop_id)
        .order_by(Product.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, product_id: UUID, shop_id: UUID) -> Product | None:
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id, Product.shop_id == shop_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    shop_id: UUID,
    category_id: UUID,
    name: str,
    description: str,
    price: float,
    discount_price: float | None,
    image_url: str | None,
    image_public_id: str | None,
    in_stock: bool,
) -> Product:
    product = Product(
        shop_id=shop_id,
        category_id=category_id,
        name=name,
        description=description,
        price=price,
        discount_price=discount_price,
        image_url=image_url,
        image_public_id=image_public_id,
        in_stock=in_stock,
    )
    session.add(product)
    await session.flush()
    return product


async def delete(session: AsyncSession, product: Product) -> None:
    await session.delete(product)
    await session.flush()
