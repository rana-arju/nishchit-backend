from app.schemas.common.response import ApiResponse, PaginatedResponse, PaginationMeta


def success[T](data: T, message: str = "Success", status_code: int = 200) -> ApiResponse[T]:
    return ApiResponse[T](success=True, status_code=status_code, message=message, data=data)


def paginated[T](
    items: list[T],
    meta: PaginationMeta,
    message: str = "Success",
    status_code: int = 200,
) -> PaginatedResponse[T]:
    return PaginatedResponse[T](
        success=True,
        status_code=status_code,
        message=message,
        meta=meta,
        data=items,
    )
