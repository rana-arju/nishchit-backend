from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.models.enums import PaymentMethod
from app.models.order import Order
from app.models.order_item import OrderItem


async def list_by_shop(session: AsyncSession, shop_id: UUID) -> list[Order]:
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.notes))
        .where(Order.shop_id == shop_id)
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, order_id: UUID, shop_id: UUID) -> Order | None:
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.notes))
        .where(Order.id == order_id, Order.shop_id == shop_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def next_order_number(session: AsyncSession, shop_id: UUID) -> str:
    stmt = select(func.count()).select_from(Order).where(Order.shop_id == shop_id)
    result = await session.execute(stmt)
    count = result.scalar_one()
    return str(1001 + count)


async def create(
    session: AsyncSession,
    *,
    shop_id: UUID,
    order_number: str,
    customer_name: str,
    customer_phone: str,
    address: str,
    channel: str,
    payment_method: PaymentMethod,
    courier: str | None,
    is_high_risk: bool,
    tags: list[str],
    items: list[OrderItem],
) -> Order:
    order = Order(
        shop_id=shop_id,
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        address=address,
        channel=channel,
        payment_method=payment_method,
        courier=courier,
        is_high_risk=is_high_risk,
        tags=tags,
        items=items,
    )
    session.add(order)
    await session.flush()
    # The items collection was populated before the flush, so SQLAlchemy already knows its
    # state, but notes was never touched. Setting it directly would make SQLAlchemy load the
    # old value first to diff it, which triggers an async-unsafe lazy load. set_committed_value
    # marks the empty collection as loaded without going through that read.
    set_committed_value(order, "notes", [])
    return order


async def delete(session: AsyncSession, order: Order) -> None:
    await session.delete(order)
    await session.flush()
