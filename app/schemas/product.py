from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core import messages
from app.schemas.common.response import CamelModel


def _validate_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(messages.INVALID_INPUT)
    return value


class ProductCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    category_id: UUID
    price: float = Field(gt=0)
    discount_price: float | None = Field(default=None, ge=0)
    image_url: str | None = None
    image_public_id: str | None = None
    in_stock: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_discount_price(self) -> "ProductCreateRequest":
        if self.discount_price is not None and self.discount_price >= self.price:
            raise ValueError(messages.INVALID_DISCOUNT_PRICE)
        return self


class ProductUpdateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    category_id: UUID
    price: float = Field(gt=0)
    discount_price: float | None = Field(default=None, ge=0)
    image_url: str | None = None
    image_public_id: str | None = None
    in_stock: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_discount_price(self) -> "ProductUpdateRequest":
        if self.discount_price is not None and self.discount_price >= self.price:
            raise ValueError(messages.INVALID_DISCOUNT_PRICE)
        return self


class ProductRead(CamelModel):
    id: UUID
    name: str
    description: str
    category_id: UUID
    category_name: str
    price: float
    discount_price: float | None
    image_url: str | None
    image_public_id: str | None
    in_stock: bool
    created_at: datetime


class ImageUploadResponse(CamelModel):
    image_url: str
    image_public_id: str
