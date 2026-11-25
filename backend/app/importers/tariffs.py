"""Normalización conservadora e importación auditable de tarifas CSV."""

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Carrier, ImportBatch, ImportRecord, Tariff

CARRIER_ALIASES = {
    "dhl": "DHL",
    "dhlexpress": "DHL",
    "estafeta": "Estafeta",
    "estafetamexicana": "Estafeta",
    "fedex": "FedEx",
    "federalexpress": "FedEx",
    "redpack": "Redpack",
}
SPANISH_MONTHS = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3,
    "marzo": 3, "abr": 4, "abril": 4, "may": 5, "mayo": 5,
    "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8,
    "agosto": 8, "sep": 9, "sept": 9, "septiembre": 9,
    "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}


@dataclass
class NormalizedTariff:
    carrier_name: str
    zone: int
    weight_min_kg: Decimal
    weight_max_kg: Decimal
    price_mxn: Decimal
    delivery_days_min: int
    delivery_days_max: int
    valid_from: date
    messages: list[str] = field(default_factory=list)

    def fingerprint(self) -> str:
        canonical = "|".join(map(str, (
            self.carrier_name, self.zone, self.weight_min_kg,
            self.weight_max_kg, self.price_mxn, self.delivery_days_min,
            self.delivery_days_max, self.valid_from,
        )))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", value.lower())


def parse_carrier(value: str) -> tuple[str, list[str]]:
    key = _plain(value)
    canonical = CARRIER_ALIASES.get(key)
    if not canonical:
        raise ValueError(f"Paquetería desconocida: {value!r}")
    messages = []
    if value.strip() != canonical:
        messages.append(f"Paquetería normalizada: {value!r} → {canonical}")
    return canonical, messages


def parse_zone(value: str) -> tuple[int, list[str]]:
    match = re.fullmatch(r"\s*(?:zona\s*|z\s*)?(\d+)\s*", value or "", re.IGNORECASE)
    if not match:
        raise ValueError(f"Zona inválida: {value!r}")
    zone = int(match.group(1))
    if zone not in {1, 2, 3, 4}:
        raise ValueError(f"Zona fuera del catálogo permitido (1–4): {zone}")
    messages = [] if value.strip() == str(zone) else [f"Zona normalizada: {value!r} → {zone}"]
    return zone, messages


def parse_weight(value: str, unit: str, other_value: str) -> tuple[Decimal, list[str]]:
    try:
        number = Decimal((value or "").strip())
        other = Decimal((other_value or "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"Peso no numérico: {value!r}") from exc
    if number < 0:
        raise ValueError("El peso no puede ser negativo")
    normalized_unit = (unit or "").strip().lower()
    messages = []
    if normalized_unit in {"kg", "kilogramo", "kilogramos"}:
        factor = Decimal("1")
    elif normalized_unit in {"g", "gr", "gramo", "gramos"}:
        factor = Decimal("0.001")
    elif not normalized_unit:
        # Heurística acotada: un rango con límite mayor a 30 no puede
        # interpretarse razonablemente como kg para este catálogo (máx. 30 kg).
        if max(number, other) > 30:
            factor = Decimal("0.001")
            messages.append("Unidad ausente: se infirió gramos porque un límite supera 30")
        else:
            raise ValueError("Unidad de peso ausente y no inferible con seguridad")
    else:
        raise ValueError(f"Unidad de peso no reconocida: {unit!r}")
    return (number * factor).quantize(Decimal("0.001")), messages


def parse_price(value: str) -> tuple[Decimal, list[str]]:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Precio ausente")
    cleaned = re.sub(r"(?i)mxn", "", raw).replace("$", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        # El último separador se interpreta como decimal; el otro como miles.
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        tail = cleaned.rsplit(",", 1)[1]
        cleaned = cleaned.replace(",", ".") if len(tail) == 2 else cleaned.replace(",", "")
    try:
        price = Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"Precio no válido: {value!r}") from exc
    if price <= 0:
        raise ValueError("El precio debe ser mayor que cero")
    messages = [] if cleaned == raw else [f"Precio normalizado: {raw!r} → {price}"]
    return price, messages


def parse_delivery_days(value: str) -> tuple[int, int]:
    raw = (value or "").strip().lower()
    if not raw:
        raise ValueError("Días de entrega ausentes")
    match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?(?:d[ií]as?)?\s*", raw)
    if not match:
        raise ValueError(f"Días de entrega no reconocidos: {value!r}")
    minimum = int(match.group(1))
    maximum = int(match.group(2) or minimum)
    if minimum < 1 or maximum < minimum:
        raise ValueError("Rango de días de entrega inválido")
    return minimum, maximum


def parse_date(value: str) -> date:
    raw = (value or "").strip().lower()
    if not raw:
        raise ValueError("Fecha de vigencia ausente")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    match = re.fullmatch(r"(\d{1,2})-([a-záéíóú]+)-(\d{4})", raw)
    if match:
        month_key = _plain(match.group(2))
        month = SPANISH_MONTHS.get(month_key)
        if month:
            return date(int(match.group(3)), month, int(match.group(1)))
    raise ValueError(f"Fecha de vigencia no reconocida: {value!r}")


def normalize_row(row: dict[str, str]) -> NormalizedTariff:
    messages: list[str] = []
    errors: list[str] = []

    carrier = zone = None
    minimum = maximum = price = None
    days_min = days_max = valid_from = None

    try:
        carrier, items = parse_carrier(row.get("paqueteria", ""))
        messages.extend(items)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        zone, items = parse_zone(row.get("zona", ""))
        messages.extend(items)
    except ValueError as exc:
        errors.append(str(exc))

    min_raw = row.get("peso_min", row.get("peso_min_kg", ""))
    max_raw = row.get("peso_max", row.get("peso_max_kg", ""))
    unit = row.get("unidad", "")

    try:
        minimum, items = parse_weight(min_raw, unit, max_raw)
        messages.extend(items)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        maximum, items = parse_weight(max_raw, unit, min_raw)
        messages.extend(items)
    except ValueError as exc:
        errors.append(str(exc))

    if minimum is not None and maximum is not None and maximum <= minimum:
        errors.append("El peso maximo debe ser mayor que el peso minimo")

    try:
        price, items = parse_price(row.get("precio", row.get("precio_mxn", "")))
        messages.extend(items)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        days_min, days_max = parse_delivery_days(row.get("dias_entrega", ""))
    except ValueError as exc:
        errors.append(str(exc))

    try:
        valid_from = parse_date(row.get("vigencia_desde", ""))
    except ValueError as exc:
        errors.append(str(exc))

    errors = list(dict.fromkeys(errors))
    if errors:
        raise ValueError("; ".join(errors))

    messages = list(dict.fromkeys(messages))
    return NormalizedTariff(
        carrier, zone, minimum, maximum, price,
        days_min, days_max, valid_from, messages,
    )


def import_carriers(session: Session, path: Path) -> int:
    created = 0
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            code = row["carrier_id"].strip()
            name = row["nombre"].strip()
            existing = session.scalar(select(Carrier).where(Carrier.external_code == code))
            active = row["activo"].strip().lower() in {"si", "sí", "true", "1", "yes"}
            if existing:
                existing.name = name
                existing.service_type = row["tipo_servicio"].strip()
                existing.active = active
            else:
                session.add(Carrier(external_code=code, name=name, service_type=row["tipo_servicio"].strip(), active=active))
                created += 1
    session.flush()
    return created


def validate_tariff_period(
    session: Session,
    carrier_id: int,
    normalized: NormalizedTariff,
) -> list[Tariff]:
    same_tariff_range = (
        Tariff.carrier_id == carrier_id,
        Tariff.zone == normalized.zone,
        Tariff.weight_min_kg == normalized.weight_min_kg,
        Tariff.weight_max_kg == normalized.weight_max_kg,
    )

    conflicting_future = session.scalar(
        select(Tariff.id).where(
            *same_tariff_range,
            Tariff.valid_from >= normalized.valid_from,
            (
                Tariff.valid_to.is_(None)
                | (Tariff.valid_to >= normalized.valid_from)
            ),
        )
    )

    if conflicting_future:
        raise ValueError(
            "La vigencia de la tarifa se solapa con una versión "
            "posterior ya registrada"
        )

    return session.scalars(
        select(Tariff).where(
            *same_tariff_range,
            Tariff.valid_from < normalized.valid_from,
            (
                Tariff.valid_to.is_(None)
                | (Tariff.valid_to >= normalized.valid_from)
            ),
        )
    ).all()

def close_previous_tariff_versions(
    previous_versions: list[Tariff],
    new_valid_from: date,
) -> None:
    last_valid_day = new_valid_from - timedelta(days=1)

    for previous in previous_versions:
        previous.valid_to = last_valid_day


def import_tariffs(session: Session, path: Path) -> dict[str, int]:
    counts = {"accepted": 0, "corrected": 0, "rejected": 0}
    seen_in_file: set[str] = set()

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    batch = ImportBatch(source_file=path.name, total_rows=len(rows))
    session.add(batch)
    session.flush()

    carriers = {
        carrier.name: carrier
        for carrier in session.scalars(select(Carrier)).all()
    }

    for row_number, row in enumerate(rows, start=2):
        status = "rejected"
        messages: list[str] = []
        tariff_id = None

        try:
            normalized = normalize_row(row)
            messages.extend(normalized.messages)

            carrier = carriers.get(normalized.carrier_name)
            if carrier is None:
                raise ValueError(
                    f"La paquetería {normalized.carrier_name} "
                    "no existe en paqueterias.csv"
                )

            fingerprint = normalized.fingerprint()

            existing_tariff = session.scalar(
                select(Tariff.id).where(Tariff.fingerprint == fingerprint)
            )

            if fingerprint in seen_in_file or existing_tariff:
                raise ValueError(
                    "Tarifa duplicada: ya existe un registro idéntico normalizado"
                )

            previous_versions = validate_tariff_period(
                session,
                carrier.id,
                normalized,
            )

            tariff = Tariff(
                carrier_id=carrier.id,
                zone=normalized.zone,
                weight_min_kg=normalized.weight_min_kg,
                weight_max_kg=normalized.weight_max_kg,
                price_mxn=normalized.price_mxn,
                delivery_days_min=normalized.delivery_days_min,
                delivery_days_max=normalized.delivery_days_max,
                valid_from=normalized.valid_from,
                source_file=path.name,
                source_row=row_number,
                fingerprint=fingerprint,
            )

            session.add(tariff)
            session.flush()

            close_previous_tariff_versions(
                previous_versions,
                normalized.valid_from,
            )

            seen_in_file.add(fingerprint)
            tariff_id = tariff.id
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
                messages=messages,
                tariff_id=tariff_id,
            )
        )

    batch.accepted_rows = counts["accepted"]
    batch.corrected_rows = counts["corrected"]
    batch.rejected_rows = counts["rejected"]

    session.flush()
    return counts
