import asyncio
import json
import logging
from collections.abc import Sequence
from typing import cast

import asyncpg
import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError, NoResultFound, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.core import messages
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import mask_sensitive
from app.core.middleware import REQUEST_ID_HEADER
from app.schemas.common.response import ErrorDetail, ErrorResponse

logger = logging.getLogger("app.errors")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _debug_info(exc: Exception) -> str | None:
    if get_settings().environment == "local":
        return f"{type(exc).__module__}.{type(exc).__name__}"
    return None


def _log(request: Request, exc: Exception, status_code: int) -> None:
    detail = mask_sensitive(str(exc))
    message = "Unhandled error: %s | method=%s path=%s status=%s"
    args = (detail, request.method, request.url.path, status_code)
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(message, *args, exc_info=exc)
    else:
        logger.warning(message, *args)


def _build_response(
    request: Request,
    exc: Exception,
    *,
    status_code: int,
    message: str,
    error_code: str,
    errors: Sequence[ErrorDetail] | None = None,
) -> JSONResponse:
    _log(request, exc, status_code)
    request_id = _request_id(request)
    body = ErrorResponse(
        success=False,
        status_code=status_code,
        message=message,
        error_code=error_code,
        request_id=request_id,
        error_messages=list(errors) if errors else [ErrorDetail(path="", message=message)],
        debug=_debug_info(exc),
    )
    response = JSONResponse(status_code=status_code, content=body.model_dump())
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def _format_loc(loc: Sequence[int | str]) -> str:
    return ".".join(str(part) for part in loc)


async def handle_app_exception(request: Request, exc: Exception) -> JSONResponse:
    app_exc = cast(AppException, exc)
    return _build_response(
        request,
        app_exc,
        status_code=app_exc.status_code,
        message=app_exc.message,
        error_code=app_exc.error_code,
        errors=app_exc.errors,
    )


async def handle_request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    validation_exc = cast(RequestValidationError, exc)
    errors = [
        ErrorDetail(path=_format_loc(err["loc"]), message=err["msg"])
        for err in validation_exc.errors()
    ]
    return _build_response(
        request,
        validation_exc,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        message=messages.INVALID_INPUT,
        error_code="VALIDATION_ERROR",
        errors=errors,
    )


async def handle_pydantic_validation_error(request: Request, exc: Exception) -> JSONResponse:
    validation_exc = cast(ValidationError, exc)
    errors = [
        ErrorDetail(path=_format_loc(err["loc"]), message=err["msg"])
        for err in validation_exc.errors()
    ]
    return _build_response(
        request,
        validation_exc,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        message=messages.INVALID_INPUT,
        error_code="VALIDATION_ERROR",
        errors=errors,
    )


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    if http_exc.status_code == status.HTTP_404_NOT_FOUND:
        message, error_code = messages.RESOURCE_NOT_FOUND, "NOT_FOUND"
    elif http_exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        message, error_code = messages.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED"
    else:
        message, error_code = messages.GENERIC_HTTP_ERROR, "HTTP_ERROR"
    return _build_response(
        request, http_exc, status_code=http_exc.status_code, message=message, error_code=error_code
    )


def _integrity_error_detail(exc: IntegrityError) -> tuple[str, str]:
    orig = exc.orig
    if isinstance(orig, asyncpg.exceptions.ForeignKeyViolationError):
        return messages.RELATED_RECORD_CONFLICT, "RELATED_RECORD_CONFLICT"
    if isinstance(orig, asyncpg.exceptions.UniqueViolationError):
        return messages.ALREADY_EXISTS, "ALREADY_EXISTS"
    if "foreign key" in str(orig or exc).lower():
        return messages.RELATED_RECORD_CONFLICT, "RELATED_RECORD_CONFLICT"
    return messages.ALREADY_EXISTS, "ALREADY_EXISTS"


async def handle_integrity_error(request: Request, exc: Exception) -> JSONResponse:
    integrity_exc = cast(IntegrityError, exc)
    message, error_code = _integrity_error_detail(integrity_exc)
    return _build_response(
        request,
        integrity_exc,
        status_code=status.HTTP_409_CONFLICT,
        message=message,
        error_code=error_code,
    )


async def handle_no_result_found(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_404_NOT_FOUND,
        message=messages.RESOURCE_NOT_FOUND,
        error_code="NOT_FOUND",
    )


async def handle_data_error(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_400_BAD_REQUEST,
        message=messages.INVALID_DATA,
        error_code="INVALID_DATA",
    )


async def handle_service_unavailable(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        message=messages.SERVICE_UNAVAILABLE,
        error_code="SERVICE_UNAVAILABLE",
    )


async def handle_timeout(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        message=messages.REQUEST_TIMEOUT,
        error_code="REQUEST_TIMEOUT",
    )


async def handle_external_service_error(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_502_BAD_GATEWAY,
        message=messages.EXTERNAL_SERVICE_UNAVAILABLE,
        error_code="EXTERNAL_SERVICE_ERROR",
    )


async def handle_json_decode_error(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_400_BAD_REQUEST,
        message=messages.INVALID_REQUEST_BODY,
        error_code="INVALID_REQUEST_BODY",
    )


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    return _build_response(
        request,
        exc,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=messages.INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, handle_app_exception)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(ValidationError, handle_pydantic_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(NoResultFound, handle_no_result_found)
    app.add_exception_handler(DataError, handle_data_error)
    app.add_exception_handler(OperationalError, handle_service_unavailable)
    app.add_exception_handler(DBAPIError, handle_service_unavailable)
    app.add_exception_handler(httpx.TimeoutException, handle_timeout)
    app.add_exception_handler(asyncio.TimeoutError, handle_timeout)
    app.add_exception_handler(httpx.HTTPStatusError, handle_external_service_error)
    app.add_exception_handler(httpx.ConnectError, handle_external_service_error)
    app.add_exception_handler(json.JSONDecodeError, handle_json_decode_error)
    app.add_exception_handler(Exception, handle_unhandled_exception)
