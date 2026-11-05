from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.models.enums import LeadStage
from app.models.lead import Lead


async def list_by_shop(session: AsyncSession, shop_id: UUID) -> list[Lead]:
    stmt = (
        select(Lead)
        .options(selectinload(Lead.notes))
        .where(Lead.shop_id == shop_id)
        .order_by(Lead.last_activity_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, lead_id: UUID, shop_id: UUID) -> Lead | None:
    stmt = (
        select(Lead)
        .options(selectinload(Lead.notes))
        .where(Lead.id == lead_id, Lead.shop_id == shop_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    shop_id: UUID,
    name: str,
    phone: str,
    source: str,
    stage: LeadStage,
    tags: list[str],
) -> Lead:
    lead = Lead(shop_id=shop_id, name=name, phone=phone, source=source, stage=stage, tags=tags)
    session.add(lead)
    await session.flush()
    # A collection relationship can't be set directly (lead.notes = []) on a freshly flushed
    # object: SQLAlchemy reads the *old* value first to diff it, which triggers an async-unsafe
    # lazy load. set_committed_value marks it loaded without going through that read.
    set_committed_value(lead, "notes", [])
    return lead


async def delete(session: AsyncSession, lead: Lead) -> None:
    await session.delete(lead)
    await session.flush()
