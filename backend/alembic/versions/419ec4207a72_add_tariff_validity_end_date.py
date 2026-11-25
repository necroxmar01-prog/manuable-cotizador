
"""add tariff validity end date

Revision ID: 419ec4207a72
Revises: f6e48ce81a6b
Create Date: 2026-11-25 08:21:37.407335
"""
from alembic import op
import sqlalchemy as sa


revision = '419ec4207a72'
down_revision = 'f6e48ce81a6b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column("valid_to", sa.Date(), nullable=True),
    )
    op.create_index(
        op.f("ix_tariffs_valid_to"),
        "tariffs",
        ["valid_to"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tariffs_valid_to"),
        table_name="tariffs",
    )
    op.drop_column("tariffs", "valid_to")
