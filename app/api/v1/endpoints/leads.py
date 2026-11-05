from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core import messages
from app.core.responses import success
from app.models.lead import Lead
from app.schemas.common.response import ApiResponse
from app.schemas.lead import (
    LeadCreateRequest,
    LeadNoteCreateRequest,
    LeadNoteRead,
    LeadRead,
    LeadStageUpdateRequest,
    LeadTagsUpdateRequest,
    LeadUpdateRequest,
)
from app.services import lead_service

router = APIRouter(prefix="/leads", tags=["leads"])


def _to_read(lead: Lead) -> LeadRead:
    return LeadRead(
        id=lead.id,
        name=lead.name,
        phone=lead.phone,
        source=lead.source,
        stage=lead.stage,
        tags=list(lead.tags),
        notes=[
            LeadNoteRead(id=note.id, text=note.text, created_at=note.created_at)
            for note in lead.notes
        ],
        last_activity_at=lead.last_activity_at,
    )


@router.get("", response_model=ApiResponse[list[LeadRead]])
async def list_leads(session: DbSession, current_user: CurrentUser) -> ApiResponse[list[LeadRead]]:
    leads = await lead_service.list_leads(session, user=current_user)
    return success(data=[_to_read(lead) for lead in leads], message=messages.LEADS_FETCHED)


@router.get("/{lead_id}", response_model=ApiResponse[LeadRead])
async def get_lead(
    lead_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[LeadRead]:
    lead = await lead_service.get_lead(session, user=current_user, lead_id=lead_id)
    return success(data=_to_read(lead), message=messages.LEAD_FETCHED)


@router.post("", response_model=ApiResponse[LeadRead], status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreateRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[LeadRead]:
    lead = await lead_service.create_lead(
        session,
        user=current_user,
        name=payload.name,
        phone=payload.phone,
        source=payload.source,
        stage=payload.stage,
        tags=payload.tags,
    )
    return success(
        data=_to_read(lead), message=messages.LEAD_CREATED, status_code=status.HTTP_201_CREATED
    )


@router.patch("/{lead_id}", response_model=ApiResponse[LeadRead])
async def update_lead(
    lead_id: UUID, payload: LeadUpdateRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[LeadRead]:
    lead = await lead_service.update_lead(
        session,
        user=current_user,
        lead_id=lead_id,
        name=payload.name,
        phone=payload.phone,
        source=payload.source,
    )
    return success(data=_to_read(lead), message=messages.LEAD_UPDATED)


@router.patch("/{lead_id}/stage", response_model=ApiResponse[LeadRead])
async def update_lead_stage(
    lead_id: UUID,
    payload: LeadStageUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[LeadRead]:
    lead = await lead_service.update_stage(
        session, user=current_user, lead_id=lead_id, stage=payload.stage
    )
    return success(data=_to_read(lead), message=messages.LEAD_STAGE_UPDATED)


@router.put("/{lead_id}/tags", response_model=ApiResponse[LeadRead])
async def update_lead_tags(
    lead_id: UUID,
    payload: LeadTagsUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[LeadRead]:
    lead = await lead_service.update_tags(
        session, user=current_user, lead_id=lead_id, tags=payload.tags
    )
    return success(data=_to_read(lead), message=messages.LEAD_TAGS_UPDATED)


@router.post(
    "/{lead_id}/notes", response_model=ApiResponse[LeadRead], status_code=status.HTTP_201_CREATED
)
async def add_lead_note(
    lead_id: UUID,
    payload: LeadNoteCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[LeadRead]:
    lead = await lead_service.add_note(
        session, user=current_user, lead_id=lead_id, text=payload.text
    )
    return success(
        data=_to_read(lead), message=messages.NOTE_ADDED, status_code=status.HTTP_201_CREATED
    )


@router.delete("/{lead_id}", response_model=ApiResponse[None])
async def delete_lead(
    lead_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[None]:
    await lead_service.delete_lead(session, user=current_user, lead_id=lead_id)
    return success(data=None, message=messages.LEAD_DELETED)
