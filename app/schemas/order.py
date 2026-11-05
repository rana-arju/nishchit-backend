from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core import messages
from app.models.enums import OrderStatus, PaymentMethod
from app.schemas.common.response import CamelModel


def _validate_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(messages.INVALID_INPUT)
    return value


def _clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for tag in tags:
        stripped = tag.strip()
        if stripped and stripped not in cleaned:
            cleaned.append(stripped)
    return cleaned


class OrderItemCreateRequest(CamelModel):
    product_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, value: str) -> str:
        return _validate_required_text(value)


class OrderItemRead(CamelModel):
    id: UUID
    product_name: str
    quantity: int
    price: float


class OrderNoteCreateRequest(CamelModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_required_text(value)


class OrderNoteRead(CamelModel):
    id: UUID
    text: str
    created_at: datetime


class OrderCreateRequest(CamelModel):
    customer_name: str = Field(min_length=1, max_length=150)
    customer_phone: str = Field(min_length=1, max_length=32)
    address: str = Field(min_length=1, max_length=300)
    channel: str = Field(default="manual", max_length=50)
    payment_method: PaymentMethod = PaymentMethod.COD
    courier: str | None = Field(default=None, max_length=50)
    is_high_risk: bool = False
    tags: list[str] = Field(default_factory=list)
    items: list[OrderItemCreateRequest] = Field(min_length=1)

    @field_validator("customer_name", "customer_phone", "address")
    @classmethod
    def validate_required(cls, value: str) -> str:
        return _validate_required_text(value)

    @field_validator("channel")
    @classmethod
    def strip_channel(cls, value: str) -> str:
        return value.strip() or "manual"

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return _clean_tags(value)


class OrderUpdateRequest(CamelModel):
    customer_name: str = Field(min_length=1, max_length=150)
    customer_phone: str = Field(min_length=1, max_length=32)
    address: str = Field(min_length=1, max_length=300)
    channel: str = Field(min_length=1, max_length=50)
    payment_method: PaymentMethod
    courier: str | None = Field(default=None, max_length=50)
    is_high_risk: bool = False
    items: list[OrderItemCreateRequest] = Field(min_length=1)

    @field_validator("customer_name", "customer_phone", "address", "channel")
    @classmethod
    def validate_required(cls, value: str) -> str:
        return _validate_required_text(value)


class OrderStatusUpdateRequest(CamelModel):
    status: OrderStatus


class OrderTagsUpdateRequest(CamelModel):
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return _clean_tags(value)


class OrderRead(CamelModel):
    id: UUID
    order_number: str
    customer_name: str
    customer_phone: str
    address: str
    channel: str
    status: OrderStatus
    payment_method: PaymentMethod
    courier: str | None
    is_high_risk: bool
    items: list[OrderItemRead]
    tags: list[str]
    notes: list[OrderNoteRead]
    created_at: datetime
