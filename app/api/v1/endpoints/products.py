from uuid import UUID

from fastapi import APIRouter, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.core import messages
from app.core.responses import success
from app.models.product import Product
from app.schemas.common.response import ApiResponse
from app.schemas.product import (
    ImageUploadResponse,
    ProductCreateRequest,
    ProductRead,
    ProductUpdateRequest,
)
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


def _to_read(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name,
        price=product.price,
        discount_price=product.discount_price,
        image_url=product.image_url,
        image_public_id=product.image_public_id,
        in_stock=product.in_stock,
        created_at=product.created_at,
    )


@router.get("", response_model=ApiResponse[list[ProductRead]])
async def list_products(
    session: DbSession, current_user: CurrentUser
) -> ApiResponse[list[ProductRead]]:
    products = await product_service.list_products(session, user=current_user)
    return success(
        data=[_to_read(product) for product in products], message=messages.PRODUCTS_FETCHED
    )


@router.get("/{product_id}", response_model=ApiResponse[ProductRead])
async def get_product(
    product_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[ProductRead]:
    product = await product_service.get_product(session, user=current_user, product_id=product_id)
    return success(data=_to_read(product), message=messages.PRODUCT_FETCHED)


@router.post("", response_model=ApiResponse[ProductRead], status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreateRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[ProductRead]:
    product = await product_service.create_product(
        session,
        user=current_user,
        name=payload.name,
        description=payload.description,
        category_id=payload.category_id,
        price=payload.price,
        discount_price=payload.discount_price,
        image_url=payload.image_url,
        image_public_id=payload.image_public_id,
        in_stock=payload.in_stock,
    )
    return success(
        data=_to_read(product),
        message=messages.PRODUCT_CREATED,
        status_code=status.HTTP_201_CREATED,
    )


@router.patch("/{product_id}", response_model=ApiResponse[ProductRead])
async def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ProductRead]:
    product = await product_service.update_product(
        session,
        user=current_user,
        product_id=product_id,
        name=payload.name,
        description=payload.description,
        category_id=payload.category_id,
        price=payload.price,
        discount_price=payload.discount_price,
        image_url=payload.image_url,
        image_public_id=payload.image_public_id,
        in_stock=payload.in_stock,
    )
    return success(data=_to_read(product), message=messages.PRODUCT_UPDATED)


@router.delete("/{product_id}", response_model=ApiResponse[None])
async def delete_product(
    product_id: UUID, session: DbSession, current_user: CurrentUser
) -> ApiResponse[None]:
    await product_service.delete_product(session, user=current_user, product_id=product_id)
    return success(data=None, message=messages.PRODUCT_DELETED)


@router.post("/upload-image", response_model=ApiResponse[ImageUploadResponse])
async def upload_product_image(
    current_user: CurrentUser, file: UploadFile
) -> ApiResponse[ImageUploadResponse]:
    content = await file.read()
    image_url, image_public_id = await product_service.upload_product_image(
        content, file.content_type or ""
    )
    return success(
        data=ImageUploadResponse(image_url=image_url, image_public_id=image_public_id),
        message=messages.IMAGE_UPLOADED,
    )
