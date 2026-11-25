"""Carga de reglas de peso cobrable (real / volumétrico) desde CSV.

Formato: paqueteria,metodo,divisor_volumetrico,vigencia_desde
Cuando Estafeta renueve contrato basta con agregar una fila, p. ej.
``Estafeta,volumetrico,5000,2027-03-01``; no se toca código.
"""

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.tariffs import file_sha256, parse_carrier, parse_date
from app.models import Carrier, CarrierPricingRule, ImportBatch, ImportRecord
from app.models.carrier_pricing_rule import WEIGHT_METHOD_REAL, WEIGHT_METHOD_VOLUMETRIC

METHOD_ALIASES = {
    "real": WEIGHT_METHOD_REAL,
    "volumetrico": WEIGHT_METHOD_VOLUMETRIC,
    "volumétrico": WEIGHT_METHOD_VOLUMETRIC,
}


def import_pricing_rules(session: Session, path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    batch = ImportBatch(
        source_file=path.name,
        kind="pricing_rules",
        file_sha256=file_sha256(path),
        total_rows=len(rows),
    )
    session.add(batch)
    session.flush()

    carriers = {c.name: c for c in session.scalars(select(Carrier)).all()}
    counts = {"accepted": 0, "rejected": 0}

    for row_number, row in enumerate(rows, start=2):
        messages: list[str] = []
        status = "rejected"
        try:
            carrier_name, _ = parse_carrier(row.get("paqueteria", ""))
            carrier = carriers.get(carrier_name)
            if carrier is None:
                raise ValueError(f"La paquetería {carrier_name} no existe en el catálogo")

            method = METHOD_ALIASES.get((row.get("metodo") or "").strip().lower())
            if method is None:
                raise ValueError(f"Método de peso desconocido: {row.get('metodo')!r}")

            divisor = None
            if method == WEIGHT_METHOD_VOLUMETRIC:
                raw_divisor = (row.get("divisor_volumetrico") or "").strip()
                if not raw_divisor.isdigit() or int(raw_divisor) <= 0:
                    raise ValueError("El método volumétrico requiere un divisor entero positivo")
                divisor = int(raw_divisor)

            valid_from = parse_date(row.get("vigencia_desde", ""))

            rule = session.scalar(
                select(CarrierPricingRule).where(
                    CarrierPricingRule.carrier_id == carrier.id,
                    CarrierPricingRule.valid_from == valid_from,
                )
            )
            if rule is None:
                rule = CarrierPricingRule(carrier_id=carrier.id, valid_from=valid_from)
                session.add(rule)
            elif (rule.weight_method, rule.volumetric_divisor) != (method, divisor):
                messages.append("Regla existente actualizada para esa fecha")
            rule.weight_method = method
            rule.volumetric_divisor = divisor
            rule.source_file = path.name
            status = "accepted"
        except ValueError as exc:
            messages.append(str(exc))

        counts[status] += 1
        session.add(
            ImportRecord(
                batch_id=batch.id,
                row_number=row_number,
                status=status,
                raw_data=row,
                messages=messages,
            )
        )

    batch.accepted_rows = counts["accepted"]
    batch.rejected_rows = counts["rejected"]
    session.flush()
    return counts
