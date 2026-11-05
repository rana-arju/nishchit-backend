"""add oauth provider support to users

Revision ID: 05087d7ad449
Revises: e2663bcf8c58
Create Date: 2026-11-05 23:31:37.909022

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "05087d7ad449"
down_revision: str | Sequence[str] | None = "e2663bcf8c58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.Enum(
                "local", "google", "facebook", name="auth_provider", native_enum=False, length=20
            ),
            server_default="local",
            nullable=False,
        ),
    )
    op.alter_column("users", "password_hash", existing_type=sa.VARCHAR(length=255), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("users", "password_hash", existing_type=sa.VARCHAR(length=255), nullable=False)
    op.drop_column("users", "auth_provider")
