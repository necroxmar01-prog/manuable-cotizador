
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CarrierPricingRule(Base):
    __tablename__ = "carrier_pricing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(
        ForeignKey("carriers.id"),
        index=True,
        nullable=False,
    )
    weight_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    volumetric_divisor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    carrier = relationship("Carrier")
