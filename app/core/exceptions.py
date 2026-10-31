from fastapi import status

from app.core import messages
from app.schemas.common.response import ErrorDetail


class AppException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"
    message: str = messages.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        errors: list[ErrorDetail] | None = None,
    ) -> None:
        self.message = message or self.message
        self.error_code = error_code or self.error_code
        self.status_code = status_code or self.status_code
        self.errors = errors
        super().__init__(self.message)


class BadRequest(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    message = messages.BAD_REQUEST


class Unauthorized(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    message = messages.UNAUTHORIZED


class Forbidden(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"
    message = messages.FORBIDDEN


class NotFound(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = messages.RESOURCE_NOT_FOUND


class Conflict(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = messages.CONFLICT


class UnprocessableEntity(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "UNPROCESSABLE_ENTITY"
    message = messages.INVALID_INPUT


class TooManyRequests(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "TOO_MANY_REQUESTS"
    message = messages.TOO_MANY_REQUESTS


class ServiceUnavailable(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = messages.SERVICE_UNAVAILABLE


class ExternalServiceError(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "EXTERNAL_SERVICE_ERROR"
    message = messages.EXTERNAL_SERVICE_UNAVAILABLE
