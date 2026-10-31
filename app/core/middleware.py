import contextvars
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core import messages
from app.schemas.common.response import ErrorDetail, ErrorResponse

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        super().__init__(app)
        self._max_body_bytes = max_body_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > self._max_body_bytes:
            request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
            body = ErrorResponse(
                success=False,
                status_code=413,
                message=messages.REQUEST_ENTITY_TOO_LARGE,
                error_code="PAYLOAD_TOO_LARGE",
                request_id=request_id,
                error_messages=[ErrorDetail(path="", message=messages.REQUEST_ENTITY_TOO_LARGE)],
            )
            return JSONResponse(status_code=413, content=body.model_dump())
        return await call_next(request)
