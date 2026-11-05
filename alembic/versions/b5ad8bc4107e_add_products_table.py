"""add products table

Revision ID: b5ad8bc4107e
Revises: b9c05a893451
Create Date: 2026-11-06 01:06:24.602538

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5ad8bc4107e"
down_revision: str | Sequence[str] | None = "b9c05a893451"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "products",
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=False),
        sa.Column(
            "discount_price", sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=True
        ),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("image_public_id", sa.String(length=255), nullable=True),
        sa.Column("in_stock", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_products_category_id_categories")
        ),
        sa.ForeignKeyConstraint(
            ["shop_id"], ["shops.id"], name=op.f("fk_products_shop_id_shops")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_index(op.f("ix_products_shop_id"), "products", ["shop_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_products_shop_id"), table_name="products")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_table("products")
