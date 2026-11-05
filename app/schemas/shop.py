from uuid import UUID

from app.schemas.common.response import CamelModel


class ShopRead(CamelModel):
    id: UUID
    name: str
