import re

from pydantic import Field, field_validator

from app.core import messages
from app.schemas.common.response import CamelModel

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_PATTERN.match(value):
        raise ValueError(messages.INVALID_EMAIL)
    return value


class RegisterRequest(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    shop_name: str = Field(min_length=1, max_length=150)
    email: str
    password: str = Field(min_length=6, max_length=128)

    @field_validator("name", "shop_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class LoginRequest(CamelModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class SetShopRequest(CamelModel):
    shop_name: str = Field(min_length=1, max_length=150)

    @field_validator("shop_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


_OTP_PATTERN = re.compile(r"^\d{6}$")


def _validate_otp(value: str) -> str:
    value = value.strip()
    if not _OTP_PATTERN.match(value):
        raise ValueError(messages.INVALID_OTP)
    return value


class ForgotPasswordRequest(CamelModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class VerifyOtpRequest(CamelModel):
    email: str
    otp: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        return _validate_otp(value)


class ResetPasswordRequest(CamelModel):
    email: str
    otp: str
    new_password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        return _validate_otp(value)


class ChangePasswordRequest(CamelModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)
