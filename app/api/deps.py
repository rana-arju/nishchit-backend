from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.cookies import ACCESS_TOKEN_COOKIE
from app.core.exceptions import Unauthorized
from app.db.session import get_session
from app.models.user import User
from app.services import auth_service


async def get_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncGenerator[AsyncSession, None]:
    yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, session: DbSession) -> User:
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not access_token:
        raise Unauthorized(messages.NOT_AUTHENTICATED, error_code="NOT_AUTHENTICATED")

    return await auth_service.get_current_user(session, access_token=access_token)


CurrentUser = Annotated[User, Depends(get_current_user)]
