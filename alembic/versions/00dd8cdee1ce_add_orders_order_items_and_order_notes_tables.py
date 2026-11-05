"""add orders, order_items and order_notes tables

Revision ID: 00dd8cdee1ce
Revises: bc20e30af02f
Create Date: 2026-11-06 02:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00dd8cdee1ce"
down_revision: str | Sequence[str] | None = "bc20e30af02f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "orders",
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=20), nullable=False),
        sa.Column("customer_name", sa.String(length=150), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("channel", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "confirmed",
                "shipped",
                "delivered",
                "cancelled",
                "returned",
                name="order_status",
                native_enum=False,
                length=20,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            sa.Enum(
                "cod",
                "prepaid",
                name="payment_method",
                native_enum=False,
                length=20,
            ),
            server_default="cod",
            nullable=False,
        ),
        sa.Column("courier", sa.String(length=50), nullable=True),
        sa.Column("is_high_risk", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("tags", sa.ARRAY(sa.String(length=50)), server_default="{}", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], name=op.f("fk_orders_shop_id_shops")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("shop_id", "order_number", name=op.f("uq_orders_shop_id")),
    )
    op.create_index(op.f("ix_orders_shop_id"), "orders", ["shop_id"], unique=False)
    op.create_table(
        "order_items",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name=op.f("fk_order_items_order_id_orders")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_table(
        "order_notes",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name=op.f("fk_order_notes_order_id_orders")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_notes")),
    )
    op.create_index(op.f("ix_order_notes_order_id"), "order_notes", ["order_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_order_notes_order_id"), table_name="order_notes")
    op.drop_table("order_notes")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_shop_id"), table_name="orders")
    op.drop_table("orders")
