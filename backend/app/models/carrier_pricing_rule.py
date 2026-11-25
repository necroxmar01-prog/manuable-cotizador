from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

WEIGHT_METHOD_REAL = "real"
WEIGHT_METHOD_VOLUMETRIC = "volumetrico"


class CarrierPricingRule(Base):
    """Cómo calcula el peso cobrable una paquetería a partir de una fecha.

    Para cada paquetería aplica la regla con la vigencia más reciente que ya
    haya iniciado. Sin regla, se cobra por peso real.
    """

    __tablename__ = "carrier_pricing_rules"
    __table_args__ = (
        UniqueConstraint("carrier_id", "valid_from", name="uq_pricing_rule_carrier_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carriers.id"), index=True, nullable=False)
    weight_method: Mapped[str] = mapped_column(String(20), nullable=False)
    volumetric_divisor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(120), nullable=True)

    carrier = relationship("Carrier")
