import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.lead import Lead


class LeadNote(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lead_notes"

    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), index=True)
    text: Mapped[str] = mapped_column(Text)

    lead: Mapped["Lead"] = relationship(back_populates="notes")
