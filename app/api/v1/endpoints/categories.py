from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core import messages
from app.core.responses import success
from app.models.category import Category
from app.schemas.category import CategoryCreateRequest, CategoryRead, CategoryUpdateRequest
from app.schemas.common.response import ApiResponse
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_read(category: Category) -> CategoryRead:
    # product_count is always 0 until the product catalog feature exists.
    return CategoryRead(
        id=category.id,
        name=category.name,
        product_count=0,
        created_at=category.created_at,
    )


@router.get("", response_model=ApiResponse[list[CategoryRead]])
async def list_categories(
    session: DbSession, current_user: CurrentUser
) -> ApiResponse[list[CategoryRead]]:
    categories = await category_service.list_categories(session, user=current_user)
    return success(
        data=[_to_read(category) for category in categories],
        message=messages.CATEGORIES_FETCHED,
    )


@router.post("", response_model=ApiResponse[CategoryRead], status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[CategoryRead]:
    category = await category_service.create_category(
        session, user=current_user, name=payload.name
    )
    return success(
        data=_to_read(category),
        message=messages.CATEGORY_CREATED,
        status_code=status.HTTP_201_CREATED,
    )


@router.patch("/{category_id}", response_model=ApiResponse[CategoryRead])
async def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[CategoryRead]:
    category = await category_service.update_category(
        session, user=current_user, category_id=category_id, name=payload.name
    )
    return success(data=_to_read(category), message=messages.CATEGORY_UPDATED)


@router.delete("/{category_id}", response_model=ApiResponse[None])
async def delete_category(
    category_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[None]:
    await category_service.delete_category(session, user=current_user, category_id=category_id)
    return success(data=None, message=messages.CATEGORY_DELETED)
