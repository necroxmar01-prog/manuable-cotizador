from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuoteOption(Base):
    """Foto inmutable de lo que vio la persona: no se recalcula nunca."""

    __tablename__ = "quote_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), index=True)
    carrier_name: Mapped[str] = mapped_column(String(80))
    service_type: Mapped[str] = mapped_column(String(40))
    price_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Nulos en cotizaciones telefónicas, que no registraron plazo.
    delivery_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billable_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    weight_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tariff_id: Mapped[int | None] = mapped_column(ForeignKey("tariffs.id"), nullable=True)

    quote = relationship("Quote", back_populates="options")
