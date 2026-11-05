from uuid import UUID

from app.schemas.common.response import CamelModel
from app.schemas.shop import ShopRead


class UserRead(CamelModel):
    id: UUID
    name: str
    email: str
    shop: ShopRead | None
