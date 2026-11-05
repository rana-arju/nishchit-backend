from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import AuthProvider

if TYPE_CHECKING:
    from app.models.shop import Shop


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[AuthProvider] = mapped_column(
        SAEnum(
            AuthProvider,
            name="auth_provider",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=AuthProvider.LOCAL,
        server_default=AuthProvider.LOCAL.value,
    )

    shop: Mapped["Shop | None"] = relationship(back_populates="owner", uselist=False)
