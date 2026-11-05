from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import BadRequest, NotFound
from app.models.enums import LeadStage
from app.models.lead import Lead
from app.models.lead_note import LeadNote
from app.models.user import User
from app.repositories import lead_repository


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _require_shop_id(user: User) -> UUID:
    if user.shop is None:
        raise BadRequest(messages.SHOP_REQUIRED, error_code="SHOP_REQUIRED")
    return user.shop.id


async def _get_lead_or_raise(session: AsyncSession, *, shop_id: UUID, lead_id: UUID) -> Lead:
    lead = await lead_repository.get_by_id(session, lead_id, shop_id)
    if lead is None:
        raise NotFound(messages.LEAD_NOT_FOUND, error_code="LEAD_NOT_FOUND")
    return lead


async def list_leads(session: AsyncSession, *, user: User) -> list[Lead]:
    if user.shop is None:
        return []
    return await lead_repository.list_by_shop(session, user.shop.id)


async def get_lead(session: AsyncSession, *, user: User, lead_id: UUID) -> Lead:
    shop_id = _require_shop_id(user)
    return await _get_lead_or_raise(session, shop_id=shop_id, lead_id=lead_id)


async def create_lead(
    session: AsyncSession,
    *,
    user: User,
    name: str,
    phone: str,
    source: str,
    stage: LeadStage,
    tags: list[str],
) -> Lead:
    shop_id = _require_shop_id(user)
    lead = await lead_repository.create(
        session, shop_id=shop_id, name=name, phone=phone, source=source, stage=stage, tags=tags
    )
    await session.commit()
    return lead


async def update_lead(
    session: AsyncSession, *, user: User, lead_id: UUID, name: str, phone: str, source: str
) -> Lead:
    shop_id = _require_shop_id(user)
    lead = await _get_lead_or_raise(session, shop_id=shop_id, lead_id=lead_id)

    lead.name = name
    lead.phone = phone
    lead.source = source
    lead.last_activity_at = _utcnow()
    await session.commit()

    return lead


async def update_stage(
    session: AsyncSession, *, user: User, lead_id: UUID, stage: LeadStage
) -> Lead:
    shop_id = _require_shop_id(user)
    lead = await _get_lead_or_raise(session, shop_id=shop_id, lead_id=lead_id)

    lead.stage = stage
    lead.last_activity_at = _utcnow()
    await session.commit()

    return lead


async def update_tags(session: AsyncSession, *, user: User, lead_id: UUID, tags: list[str]) -> Lead:
    shop_id = _require_shop_id(user)
    lead = await _get_lead_or_raise(session, shop_id=shop_id, lead_id=lead_id)

    lead.tags = tags
    lead.last_activity_at = _utcnow()
    await session.commit()

    return lead


async def add_note(session: AsyncSession, *, user: User, lead_id: UUID, text: str) -> Lead:
    shop_id = _require_shop_id(user)
    lead = await _get_lead_or_raise(session, shop_id=shop_id, lead_id=lead_id)

    note = LeadNote(lead_id=lead.id, text=text)
    session.add(note)
    lead.notes.append(note)
    lead.last_activity_at = _utcnow()
    await session.commit()

    return lead


async def delete_lead(session: AsyncSession, *, user: User, lead_id: UUID) -> None:
    shop_id = _require_shop_id(user)
    lead = await _get_lead_or_raise(session, shop_id=shop_id, lead_id=lead_id)

    await lead_repository.delete(session, lead)
    await session.commit()
