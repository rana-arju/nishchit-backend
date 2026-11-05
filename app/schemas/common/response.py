from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


class PaginationMeta(CamelModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ApiResponse[T](CamelModel):
    success: bool = True
    status_code: int
    message: str
    data: T


class PaginatedResponse[T](CamelModel):
    success: bool = True
    status_code: int
    message: str
    meta: PaginationMeta
    data: list[T]


class ErrorDetail(CamelModel):
    path: str
    message: str


class ErrorResponse(CamelModel):
    success: bool = False
    status_code: int
    message: str
    error_code: str
    request_id: str
    error_messages: list[ErrorDetail]
    debug: str | None = None
