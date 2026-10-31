from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health import HealthStatus


async def check_health(session: AsyncSession) -> HealthStatus:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        return HealthStatus(status="degraded", database="unreachable")

    return HealthStatus(status="ok", database="ok")
