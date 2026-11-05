"""add leads and lead_notes tables

Revision ID: bc20e30af02f
Revises: b5ad8bc4107e
Create Date: 2026-11-06 01:35:17.415350

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bc20e30af02f"
down_revision: str | Sequence[str] | None = "b5ad8bc4107e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "leads",
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "stage",
            sa.Enum(
                "new",
                "contacted",
                "interested",
                "follow_up",
                "qualified",
                "order_confirmed",
                "lost",
                name="lead_stage",
                native_enum=False,
                length=20,
            ),
            server_default="new",
            nullable=False,
        ),
        sa.Column("tags", sa.ARRAY(sa.String(length=50)), server_default="{}", nullable=False),
        sa.Column(
            "last_activity_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], name=op.f("fk_leads_shop_id_shops")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index(op.f("ix_leads_shop_id"), "leads", ["shop_id"], unique=False)
    op.create_table(
        "lead_notes",
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_lead_notes_lead_id_leads")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lead_notes")),
    )
    op.create_index(op.f("ix_lead_notes_lead_id"), "lead_notes", ["lead_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_lead_notes_lead_id"), table_name="lead_notes")
    op.drop_table("lead_notes")
    op.drop_index(op.f("ix_leads_shop_id"), table_name="leads")
    op.drop_table("leads")
