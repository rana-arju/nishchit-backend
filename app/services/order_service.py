from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import BadRequest, NotFound
from app.models.enums import OrderStatus, PaymentMethod
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_note import OrderNote
from app.models.user import User
from app.repositories import order_repository
from app.schemas.order import OrderItemCreateRequest


def _require_shop_id(user: User) -> UUID:
    if user.shop is None:
        raise BadRequest(messages.SHOP_REQUIRED, error_code="SHOP_REQUIRED")
    return user.shop.id


async def _get_order_or_raise(session: AsyncSession, *, shop_id: UUID, order_id: UUID) -> Order:
    order = await order_repository.get_by_id(session, order_id, shop_id)
    if order is None:
        raise NotFound(messages.ORDER_NOT_FOUND, error_code="ORDER_NOT_FOUND")
    return order


def _to_items(items: list[OrderItemCreateRequest]) -> list[OrderItem]:
    return [
        OrderItem(product_name=item.product_name, quantity=item.quantity, price=item.price)
        for item in items
    ]


async def list_orders(session: AsyncSession, *, user: User) -> list[Order]:
    if user.shop is None:
        return []
    return await order_repository.list_by_shop(session, user.shop.id)


async def get_order(session: AsyncSession, *, user: User, order_id: UUID) -> Order:
    shop_id = _require_shop_id(user)
    return await _get_order_or_raise(session, shop_id=shop_id, order_id=order_id)


async def create_order(
    session: AsyncSession,
    *,
    user: User,
    customer_name: str,
    customer_phone: str,
    address: str,
    channel: str,
    payment_method: PaymentMethod,
    courier: str | None,
    is_high_risk: bool,
    tags: list[str],
    items: list[OrderItemCreateRequest],
) -> Order:
    shop_id = _require_shop_id(user)
    order_number = await order_repository.next_order_number(session, shop_id)
    order = await order_repository.create(
        session,
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
        items=_to_items(items),
    )
    await session.commit()
    return order


async def update_order(
    session: AsyncSession,
    *,
    user: User,
    order_id: UUID,
    customer_name: str,
    customer_phone: str,
    address: str,
    channel: str,
    payment_method: PaymentMethod,
    courier: str | None,
    is_high_risk: bool,
    items: list[OrderItemCreateRequest],
) -> Order:
    shop_id = _require_shop_id(user)
    order = await _get_order_or_raise(session, shop_id=shop_id, order_id=order_id)

    order.customer_name = customer_name
    order.customer_phone = customer_phone
    order.address = address
    order.channel = channel
    order.payment_method = payment_method
    order.courier = courier
    order.is_high_risk = is_high_risk
    order.items.clear()
    order.items.extend(_to_items(items))
    await session.commit()

    return order


async def update_status(
    session: AsyncSession, *, user: User, order_id: UUID, status: OrderStatus
) -> Order:
    shop_id = _require_shop_id(user)
    order = await _get_order_or_raise(session, shop_id=shop_id, order_id=order_id)

    order.status = status
    await session.commit()

    return order


async def update_tags(
    session: AsyncSession, *, user: User, order_id: UUID, tags: list[str]
) -> Order:
    shop_id = _require_shop_id(user)
    order = await _get_order_or_raise(session, shop_id=shop_id, order_id=order_id)

    order.tags = tags
    await session.commit()

    return order


async def add_note(session: AsyncSession, *, user: User, order_id: UUID, text: str) -> Order:
    shop_id = _require_shop_id(user)
    order = await _get_order_or_raise(session, shop_id=shop_id, order_id=order_id)

    note = OrderNote(order_id=order.id, text=text)
    session.add(note)
    order.notes.append(note)
    await session.commit()

    return order


async def delete_order(session: AsyncSession, *, user: User, order_id: UUID) -> None:
    shop_id = _require_shop_id(user)
    order = await _get_order_or_raise(session, shop_id=shop_id, order_id=order_id)

    await order_repository.delete(session, order)
    await session.commit()
