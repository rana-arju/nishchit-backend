import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.order import Order


class OrderNote(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "order_notes"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    text: Mapped[str] = mapped_column(Text)

    order: Mapped["Order"] = relationship(back_populates="notes")
