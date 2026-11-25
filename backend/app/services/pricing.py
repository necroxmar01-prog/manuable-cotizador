"""Resolución de tarifas y peso cobrable.

Reglas (ver DECISIONES.md):
- Tarifario vigente por paquetería: para la fecha de cotización se usa, de cada
  paquetería, el lote de tarifas con la vigencia más reciente ya iniciada. Un
  tarifario nuevo reemplaza completo al anterior, aunque sus rangos no
  coincidan uno a uno.
- Rango de peso: ``peso_min < peso <= peso_max``. Así un paquete de 1 kg cae
  en 0–1 kg y no en dos rangos a la vez (confirmado con las cotizaciones
  históricas de Comercial).
- Peso cobrable: según la regla vigente de cada paquetería (real o
  volumétrico). Ambas cosas viven en la base de datos, no en el código.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import business_date
from app.models import Carrier, CarrierPricingRule, Tariff
from app.models.carrier_pricing_rule import WEIGHT_METHOD_REAL, WEIGHT_METHOD_VOLUMETRIC

WEIGHT_QUANTUM = Decimal("0.001")


@dataclass(frozen=True)
class Package:
    weight_kg: Decimal
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None

    @property
    def has_dimensions(self) -> bool:
        return None not in (self.length_cm, self.width_cm, self.height_cm)


@dataclass(frozen=True)
class PricedOption:
    tariff: Tariff
    billable_weight_kg: Decimal
    weight_method: str


@dataclass
class PricingResult:
    options: list[PricedOption]
    notices: list[str]


def weight_in_range(tariff: Tariff, weight_kg: Decimal) -> bool:
    return Decimal(tariff.weight_min_kg) < weight_kg <= Decimal(tariff.weight_max_kg)


def effective_tariffs(db: Session, zone: int, quote_date: date) -> list[Tariff]:
    """Tarifas cotizables de la zona: solo el tarifario vigente de cada paquetería."""

    candidates = db.scalars(
        select(Tariff)
        .join(Tariff.carrier)
        .options(joinedload(Tariff.carrier))
        .where(
            Carrier.active.is_(True),
            Tariff.active.is_(True),
            Tariff.zone == zone,
            Tariff.valid_from <= quote_date,
            or_(Tariff.valid_to.is_(None), Tariff.valid_to >= quote_date),
        )
    ).all()

    latest: dict[int, date] = {}
    for tariff in candidates:
        if tariff.carrier_id not in latest or tariff.valid_from > latest[tariff.carrier_id]:
            latest[tariff.carrier_id] = tariff.valid_from

    return [t for t in candidates if t.valid_from == latest[t.carrier_id]]


def get_available_tariffs(
    db: Session,
    zone: int,
    weight_kg: Decimal,
    quote_date: date | None = None,
) -> list[Tariff]:
    """Tarifas vigentes para un peso ya cobrable, ordenadas por precio."""

    effective_date = quote_date or business_date()
    weight = Decimal(weight_kg)
    matches = [t for t in effective_tariffs(db, zone, effective_date) if weight_in_range(t, weight)]
    return sorted(matches, key=lambda t: Decimal(t.price_mxn))


def pricing_rules_for(db: Session, quote_date: date) -> dict[int, CarrierPricingRule]:
    """Regla de peso vigente por paquetería (la más reciente ya iniciada)."""

    rules = db.scalars(
        select(CarrierPricingRule)
        .where(CarrierPricingRule.valid_from <= quote_date)
        .order_by(CarrierPricingRule.valid_from)
    ).all()
    return {rule.carrier_id: rule for rule in rules}


def volumetric_weight(package: Package, divisor: int) -> Decimal:
    volume = package.length_cm * package.width_cm * package.height_cm
    return (volume / Decimal(divisor)).quantize(WEIGHT_QUANTUM, rounding=ROUND_UP)


def billable_weight(package: Package, rule: CarrierPricingRule | None) -> tuple[Decimal, str] | None:
    """Peso a cobrar y método. ``None`` si la regla exige medidas y no las hay."""

    real = Decimal(package.weight_kg)
    if rule is None or rule.weight_method == WEIGHT_METHOD_REAL:
        return real, WEIGHT_METHOD_REAL
    if not package.has_dimensions:
        return None
    return max(real, volumetric_weight(package, rule.volumetric_divisor)), WEIGHT_METHOD_VOLUMETRIC


def price_package(
    db: Session,
    zone: int,
    package: Package,
    quote_date: date | None = None,
) -> PricingResult:
    effective_date = quote_date or business_date()
    rules = pricing_rules_for(db, effective_date)

    by_carrier: dict[int, list[Tariff]] = defaultdict(list)
    for tariff in effective_tariffs(db, zone, effective_date):
        by_carrier[tariff.carrier_id].append(tariff)

    options: list[PricedOption] = []
    skipped_for_dimensions: list[str] = []
    for carrier_id, tariffs in by_carrier.items():
        weight = billable_weight(package, rules.get(carrier_id))
        if weight is None:
            skipped_for_dimensions.append(tariffs[0].carrier.name)
            continue
        billable, method = weight
        for tariff in tariffs:
            if weight_in_range(tariff, billable):
                options.append(PricedOption(tariff, billable, method))

    notices = []
    if skipped_for_dimensions:
        names = ", ".join(sorted(skipped_for_dimensions))
        notices.append(
            f"{names} cobra por peso volumétrico: indica largo, ancho y alto para ver su precio."
        )

    options.sort(key=lambda option: Decimal(option.tariff.price_mxn))
    return PricingResult(options=options, notices=notices)
