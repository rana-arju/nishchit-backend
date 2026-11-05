import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.lead import Lead
    from app.models.order import Order
    from app.models.product import Product
    from app.models.user import User


class Shop(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shops"

    name: Mapped[str] = mapped_column(String(150))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)

    owner: Mapped["User"] = relationship(back_populates="shop")
    categories: Mapped[list["Category"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    leads: Mapped[list["Lead"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
