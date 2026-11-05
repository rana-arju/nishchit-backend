import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.shop import Shop


class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"

    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2, asdecimal=False))
    discount_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2, asdecimal=False), default=None
    )
    image_url: Mapped[str | None] = mapped_column(String(500), default=None)
    image_public_id: Mapped[str | None] = mapped_column(String(255), default=None)
    in_stock: Mapped[bool] = mapped_column(default=True, server_default="true")

    shop: Mapped["Shop"] = relationship(back_populates="products")
    category: Mapped["Category"] = relationship(back_populates="products")
