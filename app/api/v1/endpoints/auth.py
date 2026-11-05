from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core import messages
from app.core.cookies import REFRESH_TOKEN_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.exceptions import Unauthorized
from app.core.responses import success
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SetShopRequest,
    VerifyOtpRequest,
)
from app.schemas.common.response import ApiResponse
from app.schemas.user import UserRead
from app.services import auth_service, password_reset_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest, session: DbSession, response: Response
) -> ApiResponse[UserRead]:
    result = await auth_service.register(
        session,
        name=payload.name,
        shop_name=payload.shop_name,
        email=payload.email,
        password=payload.password,
    )
    set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
    )
    return success(
        data=UserRead.model_validate(result.user),
        message=messages.REGISTRATION_SUCCESSFUL,
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login", response_model=ApiResponse[UserRead])
async def login(
    payload: LoginRequest, session: DbSession, response: Response
) -> ApiResponse[UserRead]:
    result = await auth_service.login(session, email=payload.email, password=payload.password)
    set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
    )
    return success(data=UserRead.model_validate(result.user), message=messages.LOGIN_SUCCESSFUL)


@router.post("/refresh", response_model=ApiResponse[None])
async def refresh(request: Request, session: DbSession, response: Response) -> ApiResponse[None]:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        raise Unauthorized(messages.MISSING_REFRESH_TOKEN, error_code="MISSING_REFRESH_TOKEN")

    tokens = await auth_service.refresh_access_token(session, refresh_token=refresh_token)
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return success(data=None, message=messages.TOKEN_REFRESHED)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(response: Response) -> ApiResponse[None]:
    clear_auth_cookies(response)
    return success(data=None, message=messages.LOGOUT_SUCCESSFUL)


@router.get("/me", response_model=ApiResponse[UserRead])
async def get_me(current_user: CurrentUser) -> ApiResponse[UserRead]:
    return success(data=UserRead.model_validate(current_user), message=messages.USER_FETCHED)


@router.post("/shop", response_model=ApiResponse[UserRead])
async def set_shop(
    payload: SetShopRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[UserRead]:
    user = await auth_service.set_shop(session, user=current_user, shop_name=payload.shop_name)
    return success(data=UserRead.model_validate(user), message=messages.SHOP_SAVED)


@router.post("/forgot-password", response_model=ApiResponse[None])
async def forgot_password(payload: ForgotPasswordRequest, session: DbSession) -> ApiResponse[None]:
    await password_reset_service.request_password_reset(session, email=payload.email)
    return success(data=None, message=messages.OTP_SENT)


@router.post("/verify-otp", response_model=ApiResponse[None])
async def verify_otp(payload: VerifyOtpRequest, session: DbSession) -> ApiResponse[None]:
    await password_reset_service.verify_otp(session, email=payload.email, otp=payload.otp)
    return success(data=None, message=messages.OTP_VERIFIED)


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(payload: ResetPasswordRequest, session: DbSession) -> ApiResponse[None]:
    await password_reset_service.reset_password(
        session, email=payload.email, otp=payload.otp, new_password=payload.new_password
    )
    return success(data=None, message=messages.PASSWORD_RESET_SUCCESSFUL)


@router.post("/change-password", response_model=ApiResponse[None])
async def change_password(
    payload: ChangePasswordRequest, session: DbSession, current_user: CurrentUser
) -> ApiResponse[None]:
    await auth_service.change_password(
        session,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return success(data=None, message=messages.PASSWORD_CHANGED_SUCCESSFUL)
