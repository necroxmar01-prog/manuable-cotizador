"""Esquema inicial de paqueterías, tarifas e importaciones."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carriers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("service_type", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("external_code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_carriers_external_code", "carriers", ["external_code"])
    op.create_index("ix_carriers_name", "carriers", ["name"])

    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("carrier_id", sa.Integer(), sa.ForeignKey("carriers.id"), nullable=False),
        sa.Column("zone", sa.Integer(), nullable=False),
        sa.Column("weight_min_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("weight_max_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("price_mxn", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_days_min", sa.Integer(), nullable=False),
        sa.Column("delivery_days_max", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=120), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("fingerprint", name="uq_tariffs_fingerprint"),
    )
    op.create_index("ix_tariffs_carrier_id", "tariffs", ["carrier_id"])
    op.create_index("ix_tariffs_zone", "tariffs", ["zone"])
    op.create_index("ix_tariffs_valid_from", "tariffs", ["valid_from"])

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_file", sa.String(length=120), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("corrected_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "import_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), sa.ForeignKey("tariffs.id"), nullable=True),
    )
    op.create_index("ix_import_records_batch_id", "import_records", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_import_records_batch_id", table_name="import_records")
    op.drop_table("import_records")
    op.drop_table("import_batches")
    op.drop_index("ix_tariffs_valid_from", table_name="tariffs")
    op.drop_index("ix_tariffs_zone", table_name="tariffs")
    op.drop_index("ix_tariffs_carrier_id", table_name="tariffs")
    op.drop_table("tariffs")
    op.drop_index("ix_carriers_name", table_name="carriers")
    op.drop_index("ix_carriers_external_code", table_name="carriers")
    op.drop_table("carriers")
