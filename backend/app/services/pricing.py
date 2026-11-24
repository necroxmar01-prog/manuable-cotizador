
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Carrier, Tariff


def get_available_tariffs(
    db: Session,
    zone: int,
    weight_kg: Decimal,
    quote_date: date | None = None,
) -> list[Tariff]:
    """Obtiene tarifas vigentes que cubren la zona y el peso solicitados."""

    effective_date = quote_date or date.today()

    statement = (
        select(Tariff)
        .join(Tariff.carrier)
        .options(joinedload(Tariff.carrier))
        .where(
            Carrier.active.is_(True),
            Tariff.zone == zone,
            Tariff.weight_min_kg <= weight_kg,
            Tariff.weight_max_kg >= weight_kg,
            Tariff.valid_from <= effective_date,
        )
        .order_by(Tariff.price_mxn.asc())
    )

    return list(db.scalars(statement).all())
