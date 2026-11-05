import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.shop import Shop


class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("shop_id", "name"),)

    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))

    shop: Mapped["Shop"] = relationship(back_populates="categories")
    products: Mapped[list["Product"]] = relationship(back_populates="category")
