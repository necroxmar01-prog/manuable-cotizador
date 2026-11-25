from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tariff(Base):
    __tablename__ = "tariffs"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_tariffs_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carriers.id"), index=True)
    zone: Mapped[int] = mapped_column(Integer, index=True)
    weight_min_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    weight_max_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    price_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_days_min: Mapped[int] = mapped_column(Integer)
    delivery_days_max: Mapped[int] = mapped_column(Integer)
    valid_from: Mapped[date] = mapped_column(Date, index=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    source_file: Mapped[str] = mapped_column(String(120))
    source_row: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    carrier = relationship("Carrier", back_populates="tariffs")
