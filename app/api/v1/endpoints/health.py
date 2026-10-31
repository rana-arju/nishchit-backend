from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.responses import success
from app.schemas.common.response import ApiResponse
from app.schemas.health import HealthStatus
from app.services.health_service import check_health

router = APIRouter()


@router.get("/health", response_model=ApiResponse[HealthStatus])
async def get_health(session: DbSession) -> ApiResponse[HealthStatus]:
    health_status = await check_health(session)
    return success(data=health_status, message="Health check successful!")
