from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.health import HealthStatus
from app.services.health_service import check_health

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def get_health(session: DbSession) -> HealthStatus:
    return await check_health(session)
