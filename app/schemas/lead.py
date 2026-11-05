from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core import messages
from app.models.enums import LeadStage
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


class LeadCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=32)
    source: str = Field(default="Manual", max_length=50)
    stage: LeadStage = LeadStage.NEW
    tags: list[str] = Field(default_factory=list)

    @field_validator("name", "phone")
    @classmethod
    def validate_required(cls, value: str) -> str:
        return _validate_required_text(value)

    @field_validator("source")
    @classmethod
    def strip_source(cls, value: str) -> str:
        return value.strip() or "Manual"

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return _clean_tags(value)


class LeadUpdateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=50)

    @field_validator("name", "phone", "source")
    @classmethod
    def validate_required(cls, value: str) -> str:
        return _validate_required_text(value)


class LeadStageUpdateRequest(CamelModel):
    stage: LeadStage


class LeadTagsUpdateRequest(CamelModel):
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return _clean_tags(value)


class LeadNoteCreateRequest(CamelModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_required_text(value)


class LeadNoteRead(CamelModel):
    id: UUID
    text: str
    created_at: datetime


class LeadRead(CamelModel):
    id: UUID
    name: str
    phone: str
    source: str
    stage: LeadStage
    tags: list[str]
    notes: list[LeadNoteRead]
    last_activity_at: datetime
