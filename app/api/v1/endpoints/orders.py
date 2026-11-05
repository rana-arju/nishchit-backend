from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core import messages
from app.core.responses import success
from app.models.order import Order
from app.schemas.common.response import ApiResponse
from app.schemas.order import (
    OrderCreateRequest,
    OrderItemRead,
    OrderNoteCreateRequest,
    OrderNoteRead,
    OrderRead,
    OrderStatusUpdateRequest,
    OrderTagsUpdateRequest,
    OrderUpdateRequest,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        address=order.address,
        channel=order.channel,
        status=order.status,
        payment_method=order.payment_method,
        courier=order.courier,
        is_high_risk=order.is_high_risk,
        items=[
            OrderItemRead(
                id=item.id, product_name=item.product_name, quantity=item.quantity, price=item.price
            )
            for item in order.items
        ],
        tags=list(order.tags),
        notes=[
            OrderNoteRead(id=note.id, text=note.text, created_at=note.created_at)
            for note in order.notes
        ],
        created_at=order.created_at,
    )


@router.get("", response_model=ApiResponse[list[OrderRead]])
async def list_orders(
    session: DbSession, current_user: CurrentUser
) -> ApiResponse[list[OrderRead]]:
    orders = await order_service.list_orders(session, user=current_user)
    return success(data=[_to_read(order) for order in orders], message=messages.ORDERS_FETCHED)


@router.get("/{order_id}", response_model=ApiResponse[OrderRead])
async def get_order(
    order_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[OrderRead]:
    order = await order_service.get_order(session, user=current_user, order_id=order_id)
    return success(data=_to_read(order), message=messages.ORDER_FETCHED)


@router.post("", response_model=ApiResponse[OrderRead], status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreateRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[OrderRead]:
    order = await order_service.create_order(
        session,
        user=current_user,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        address=payload.address,
        channel=payload.channel,
        payment_method=payload.payment_method,
        courier=payload.courier,
        is_high_risk=payload.is_high_risk,
        tags=payload.tags,
        items=payload.items,
    )
    return success(
        data=_to_read(order), message=messages.ORDER_CREATED, status_code=status.HTTP_201_CREATED
    )


@router.patch("/{order_id}", response_model=ApiResponse[OrderRead])
async def update_order(
    order_id: UUID, payload: OrderUpdateRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[OrderRead]:
    order = await order_service.update_order(
        session,
        user=current_user,
        order_id=order_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        address=payload.address,
        channel=payload.channel,
        payment_method=payload.payment_method,
        courier=payload.courier,
        is_high_risk=payload.is_high_risk,
        items=payload.items,
    )
    return success(data=_to_read(order), message=messages.ORDER_UPDATED)


@router.patch("/{order_id}/status", response_model=ApiResponse[OrderRead])
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[OrderRead]:
    order = await order_service.update_status(
        session, user=current_user, order_id=order_id, status=payload.status
    )
    return success(data=_to_read(order), message=messages.ORDER_STATUS_UPDATED)


@router.put("/{order_id}/tags", response_model=ApiResponse[OrderRead])
async def update_order_tags(
    order_id: UUID,
    payload: OrderTagsUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[OrderRead]:
    order = await order_service.update_tags(
        session, user=current_user, order_id=order_id, tags=payload.tags
    )
    return success(data=_to_read(order), message=messages.ORDER_TAGS_UPDATED)


@router.post(
    "/{order_id}/notes", response_model=ApiResponse[OrderRead], status_code=status.HTTP_201_CREATED
)
async def add_order_note(
    order_id: UUID,
    payload: OrderNoteCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[OrderRead]:
    order = await order_service.add_note(
        session, user=current_user, order_id=order_id, text=payload.text
    )
    return success(
        data=_to_read(order), message=messages.NOTE_ADDED, status_code=status.HTTP_201_CREATED
    )


@router.delete("/{order_id}", response_model=ApiResponse[None])
async def delete_order(
    order_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[None]:
    await order_service.delete_order(session, user=current_user, order_id=order_id)
    return success(data=None, message=messages.ORDER_DELETED)
