"""Fase 2: reglas de peso por paquetería, vigencia de cotizaciones,
cuarentena de tarifas y trazabilidad de importaciones.

Revision ID: b7d1c0a2e901
Revises: 419ec4207a72
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa


revision = "b7d1c0a2e901"
down_revision = "419ec4207a72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reglas de peso cobrable (real / volumétrico) versionadas por fecha.
    op.create_table(
        "carrier_pricing_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("carrier_id", sa.Integer(), sa.ForeignKey("carriers.id"), nullable=False),
        sa.Column("weight_method", sa.String(length=20), nullable=False),
        sa.Column("volumetric_divisor", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=120), nullable=True),
        sa.UniqueConstraint("carrier_id", "valid_from", name="uq_pricing_rule_carrier_date"),
        sa.CheckConstraint(
            "weight_method IN ('real', 'volumetrico')", name="ck_pricing_rule_method"
        ),
        sa.CheckConstraint(
            "weight_method = 'real' OR volumetric_divisor > 0",
            name="ck_pricing_rule_divisor",
        ),
    )
    op.create_index("ix_carrier_pricing_rules_carrier_id", "carrier_pricing_rules", ["carrier_id"])

    # Tarifas en cuarentena: cargadas pero no cotizables.
    op.add_column(
        "tariffs",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("tariffs", sa.Column("review_note", sa.Text(), nullable=True))

    # Importaciones idempotentes por contenido de archivo.
    op.add_column(
        "import_batches",
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="tariffs"),
    )
    op.add_column("import_batches", sa.Column("file_sha256", sa.String(length=64), nullable=True))
    op.add_column(
        "import_batches",
        sa.Column("quarantined_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_import_batches_file_sha256", "import_batches", ["file_sha256"])

    # Cotizaciones: dimensiones, origen, folio externo y vigencia de 30 días.
    op.add_column("quotes", sa.Column("length_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("quotes", sa.Column("width_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("quotes", sa.Column("height_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "quotes",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="web"),
    )
    op.add_column("quotes", sa.Column("external_ref", sa.String(length=30), nullable=True))
    op.create_unique_constraint("uq_quotes_external_ref", "quotes", ["external_ref"])
    op.alter_column("quotes", "distance_km", existing_type=sa.Numeric(10, 2), nullable=True)

    op.add_column("quotes", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))
    # Backfill: las cotizaciones de fase 1 se respetan 30 días desde su emisión
    # (fin del día 30 en hora de Monterrey). No se toca ningún precio.
    op.execute(
        """
        UPDATE quotes
        SET valid_until = (
            ((created_at AT TIME ZONE 'America/Monterrey')::date + 30 + time '23:59:59')
            AT TIME ZONE 'America/Monterrey'
        )
        """
    )
    op.alter_column("quotes", "valid_until", existing_type=sa.DateTime(timezone=True), nullable=False)

    # Opciones: peso cobrable, método y tarifa de origen; plazos opcionales
    # porque las cotizaciones telefónicas no los registraron.
    op.add_column("quote_options", sa.Column("billable_weight_kg", sa.Numeric(10, 3), nullable=True))
    op.add_column("quote_options", sa.Column("weight_method", sa.String(length=20), nullable=True))
    op.add_column(
        "quote_options",
        sa.Column("tariff_id", sa.Integer(), sa.ForeignKey("tariffs.id"), nullable=True),
    )
    op.alter_column("quote_options", "delivery_days_min", existing_type=sa.Integer(), nullable=True)
    op.alter_column("quote_options", "delivery_days_max", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Las cotizaciones telefónicas no tienen distancia ni plazo; se eliminan
    # antes de restaurar las restricciones NOT NULL de fase 1.
    op.execute(
        "DELETE FROM quote_options WHERE quote_id IN (SELECT id FROM quotes WHERE source <> 'web')"
    )
    op.execute("DELETE FROM quotes WHERE source <> 'web'")
    op.execute("DELETE FROM leads WHERE id NOT IN (SELECT lead_id FROM quotes)")
    # Sin sus tablas/columnas, estos lotes ya no tienen datos asociados; se
    # borran para que un nuevo upgrade los vuelva a importar.
    op.execute("DELETE FROM import_batches WHERE kind IN ('historical_quotes', 'pricing_rules')")

    op.alter_column("quote_options", "delivery_days_max", existing_type=sa.Integer(), nullable=False)
    op.alter_column("quote_options", "delivery_days_min", existing_type=sa.Integer(), nullable=False)
    op.drop_column("quote_options", "tariff_id")
    op.drop_column("quote_options", "weight_method")
    op.drop_column("quote_options", "billable_weight_kg")

    op.drop_column("quotes", "valid_until")
    op.alter_column("quotes", "distance_km", existing_type=sa.Numeric(10, 2), nullable=False)
    op.drop_constraint("uq_quotes_external_ref", "quotes", type_="unique")
    op.drop_column("quotes", "external_ref")
    op.drop_column("quotes", "source")
    op.drop_column("quotes", "height_cm")
    op.drop_column("quotes", "width_cm")
    op.drop_column("quotes", "length_cm")

    op.drop_index("ix_import_batches_file_sha256", table_name="import_batches")
    op.drop_column("import_batches", "quarantined_rows")
    op.drop_column("import_batches", "file_sha256")
    op.drop_column("import_batches", "kind")

    op.drop_column("tariffs", "review_note")
    op.drop_column("tariffs", "active")

    op.drop_index("ix_carrier_pricing_rules_carrier_id", table_name="carrier_pricing_rules")
    op.drop_table("carrier_pricing_rules")
