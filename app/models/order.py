import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import OrderStatus, PaymentMethod

if TYPE_CHECKING:
    from app.models.order_item import OrderItem
    from app.models.order_note import OrderNote
    from app.models.shop import Shop


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("shop_id", "order_number"),)

    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    order_number: Mapped[str] = mapped_column(String(20))
    customer_name: Mapped[str] = mapped_column(String(150))
    customer_phone: Mapped[str] = mapped_column(String(32))
    address: Mapped[str] = mapped_column(String(300))
    channel: Mapped[str] = mapped_column(String(50), default="manual", server_default="manual")
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            name="order_status",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(
            PaymentMethod,
            name="payment_method",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=PaymentMethod.COD,
        server_default=PaymentMethod.COD.value,
    )
    courier: Mapped[str | None] = mapped_column(String(50), default=None)
    is_high_risk: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")

    shop: Mapped["Shop"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.created_at"
    )
    notes: Mapped[list["OrderNote"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderNote.created_at"
    )
