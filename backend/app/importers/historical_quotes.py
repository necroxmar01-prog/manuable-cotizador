"""Registro de cotizaciones que Comercial dio por teléfono, fuera del cotizador.

Se guardan como cotizaciones con ``source='telefono'`` y el precio exacto que
se le dio a la persona: ese precio se respeta 30 días aunque la tarifa cambie.
Es idempotente por ``cotizacion_id`` (columna ``quotes.external_ref``).
"""

import csv
import re
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import BUSINESS_TZ, quote_valid_until
from app.importers.tariffs import file_sha256, parse_carrier, parse_date, parse_price
from app.models import Carrier, ImportBatch, ImportRecord, Lead, Quote, QuoteOption
from app.models.carrier_pricing_rule import WEIGHT_METHOD_REAL
from app.models.quote import QUOTE_SOURCE_PHONE
from app.services.pricing import get_available_tariffs

EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _postal_code(value: str, label: str, messages: list[str]) -> str:
    digits = re.sub(r"\s+", "", value or "")
    if re.fullmatch(r"\d{4}", digits):
        # Típico de Excel: el CP 06600 se guarda como número 6600.
        messages.append(f"{label}: se restauró el 0 inicial ({digits} → 0{digits})")
        digits = f"0{digits}"
    if not re.fullmatch(r"\d{5}", digits):
        raise ValueError(f"{label} inválido: {value!r}")
    return digits


def import_historical_quotes(session: Session, path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    batch = ImportBatch(
        source_file=path.name,
        kind="historical_quotes",
        file_sha256=file_sha256(path),
        total_rows=len(rows),
    )
    session.add(batch)
    session.flush()

    carriers = {c.name: c for c in session.scalars(select(Carrier)).all()}
    counts = {"accepted": 0, "corrected": 0, "rejected": 0}

    for row_number, row in enumerate(rows, start=2):
        messages: list[str] = []
        warnings: list[str] = []
        status = "rejected"
        try:
            reference = (row.get("cotizacion_id") or "").strip()
            if not reference:
                raise ValueError("Falta cotizacion_id")
            if session.scalar(select(Quote.id).where(Quote.external_ref == reference)):
                raise ValueError(f"La cotización {reference} ya estaba registrada")

            quote_day = parse_date(row.get("fecha", ""))
            email = (row.get("correo") or "").strip().lower()
            if not EMAIL_PATTERN.fullmatch(email):
                raise ValueError(f"Correo inválido: {row.get('correo')!r}")

            origin = _postal_code(row.get("cp_origen", ""), "CP de origen", messages)
            destination = _postal_code(row.get("cp_destino", ""), "CP de destino", messages)

            zone_raw = (row.get("zona") or "").strip()
            if zone_raw not in {"1", "2", "3", "4"}:
                raise ValueError(f"Zona inválida: {zone_raw!r}")
            zone = int(zone_raw)

            try:
                weight = Decimal((row.get("peso_kg") or "").strip()).quantize(Decimal("0.001"))
            except InvalidOperation as exc:
                raise ValueError(f"Peso inválido: {row.get('peso_kg')!r}") from exc
            if weight <= 0:
                raise ValueError("El peso debe ser mayor que cero")

            carrier_name, _ = parse_carrier(row.get("paqueteria", ""))
            carrier = carriers.get(carrier_name)
            if carrier is None:
                raise ValueError(f"La paquetería {carrier_name} no existe en el catálogo")

            price, _ = parse_price(row.get("precio_cotizado", ""))

            # Auditoría: no cambia el precio prometido, solo avisa a Comercial.
            expected = [
                t for t in get_available_tariffs(session, zone, weight, quote_day)
                if t.carrier_id == carrier.id
            ]
            if not expected:
                warnings.append("Aviso: no hay tarifa vigente cargada para esa paquetería, zona, peso y fecha")
            elif Decimal(expected[0].price_mxn) != price:
                warnings.append(
                    f"Aviso: la tarifa cargada para ese día es {expected[0].price_mxn} MXN; "
                    "se respeta el precio cotizado"
                )

            created_at = datetime.combine(quote_day, time(12, 0), tzinfo=BUSINESS_TZ)
            quote = Quote(
                origin_postal_code=origin,
                destination_postal_code=destination,
                weight_kg=weight,
                distance_km=None,
                zone=zone,
                source=QUOTE_SOURCE_PHONE,
                external_ref=reference,
                created_at=created_at,
                valid_until=quote_valid_until(created_at),
                lead=Lead(email=email, created_at=created_at),
                options=[
                    QuoteOption(
                        carrier_name=carrier.name,
                        service_type=carrier.service_type,
                        price_mxn=price,
                        delivery_days_min=None,
                        delivery_days_max=None,
                        billable_weight_kg=weight,
                        weight_method=WEIGHT_METHOD_REAL,
                    )
                ],
            )
            session.add(quote)
            session.flush()
            status = "corrected" if messages else "accepted"
        except ValueError as exc:
            messages.append(str(exc))

        counts[status] += 1
        session.add(
            ImportRecord(
                batch_id=batch.id,
                row_number=row_number,
                status=status,
                raw_data=row,
                messages=messages + warnings,
            )
        )

    batch.accepted_rows = counts["accepted"]
    batch.corrected_rows = counts["corrected"]
    batch.rejected_rows = counts["rejected"]
    session.flush()
    return counts
