from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core import messages
from app.schemas.common.response import CamelModel


def _validate_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(messages.INVALID_INPUT)
    return value


class CategoryCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name(value)


class CategoryUpdateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name(value)


class CategoryRead(CamelModel):
    id: UUID
    name: str
    product_count: int
    created_at: datetime
