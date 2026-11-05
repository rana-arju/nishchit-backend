import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import LeadStage

if TYPE_CHECKING:
    from app.models.lead_note import LeadNote
    from app.models.shop import Shop


class Lead(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "leads"

    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(50))
    stage: Mapped[LeadStage] = mapped_column(
        SAEnum(
            LeadStage,
            name="lead_stage",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=LeadStage.NEW,
        server_default=LeadStage.NEW.value,
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    last_activity_at: Mapped[datetime] = mapped_column(server_default=func.now())

    shop: Mapped["Shop"] = relationship(back_populates="leads")
    notes: Mapped[list["LeadNote"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadNote.created_at"
    )
