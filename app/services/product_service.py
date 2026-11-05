from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import BadRequest, NotFound
from app.integrations import cloudinary_storage
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.repositories import category_repository, product_repository


def _require_shop_id(user: User) -> UUID:
    if user.shop is None:
        raise BadRequest(messages.SHOP_REQUIRED, error_code="SHOP_REQUIRED")
    return user.shop.id


async def _get_category_or_raise(
    session: AsyncSession, *, shop_id: UUID, category_id: UUID
) -> Category:
    category = await category_repository.get_by_id(session, category_id, shop_id)
    if category is None:
        raise BadRequest(messages.CATEGORY_NOT_FOUND, error_code="CATEGORY_NOT_FOUND")
    return category


async def list_products(session: AsyncSession, *, user: User) -> list[Product]:
    if user.shop is None:
        return []
    return await product_repository.list_by_shop(session, user.shop.id)


async def get_product(session: AsyncSession, *, user: User, product_id: UUID) -> Product:
    shop_id = _require_shop_id(user)
    product = await product_repository.get_by_id(session, product_id, shop_id)
    if product is None:
        raise NotFound(messages.PRODUCT_NOT_FOUND, error_code="PRODUCT_NOT_FOUND")
    return product


async def create_product(
    session: AsyncSession,
    *,
    user: User,
    name: str,
    description: str,
    category_id: UUID,
    price: float,
    discount_price: float | None,
    image_url: str | None,
    image_public_id: str | None,
    in_stock: bool,
) -> Product:
    shop_id = _require_shop_id(user)
    category = await _get_category_or_raise(session, shop_id=shop_id, category_id=category_id)

    product = await product_repository.create(
        session,
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
    product.category = category
    await session.commit()

    return product


async def update_product(
    session: AsyncSession,
    *,
    user: User,
    product_id: UUID,
    name: str,
    description: str,
    category_id: UUID,
    price: float,
    discount_price: float | None,
    image_url: str | None,
    image_public_id: str | None,
    in_stock: bool,
) -> Product:
    shop_id = _require_shop_id(user)

    product = await product_repository.get_by_id(session, product_id, shop_id)
    if product is None:
        raise NotFound(messages.PRODUCT_NOT_FOUND, error_code="PRODUCT_NOT_FOUND")

    category = await _get_category_or_raise(session, shop_id=shop_id, category_id=category_id)
    old_image_public_id = product.image_public_id

    product.name = name
    product.description = description
    product.category_id = category_id
    product.category = category
    product.price = price
    product.discount_price = discount_price
    product.image_url = image_url
    product.image_public_id = image_public_id
    product.in_stock = in_stock

    await session.commit()

    if old_image_public_id and old_image_public_id != image_public_id:
        await cloudinary_storage.delete_image(old_image_public_id)

    return product


async def delete_product(session: AsyncSession, *, user: User, product_id: UUID) -> None:
    shop_id = _require_shop_id(user)

    product = await product_repository.get_by_id(session, product_id, shop_id)
    if product is None:
        raise NotFound(messages.PRODUCT_NOT_FOUND, error_code="PRODUCT_NOT_FOUND")

    image_public_id = product.image_public_id
    await product_repository.delete(session, product)
    await session.commit()

    if image_public_id:
        await cloudinary_storage.delete_image(image_public_id)


async def upload_product_image(content: bytes, content_type: str) -> tuple[str, str]:
    if len(content) > get_settings().max_image_upload_bytes:
        raise BadRequest(messages.IMAGE_TOO_LARGE, error_code="IMAGE_TOO_LARGE")
    if not content_type.startswith("image/"):
        raise BadRequest(messages.INVALID_IMAGE_TYPE, error_code="INVALID_IMAGE_TYPE")

    return await cloudinary_storage.upload_image(content)
