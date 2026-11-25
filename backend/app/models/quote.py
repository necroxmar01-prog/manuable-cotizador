from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import now, quote_valid_until
from app.db.base import Base

QUOTE_SOURCE_WEB = "web"
QUOTE_SOURCE_PHONE = "telefono"


def _default_valid_until(context) -> datetime:
    created_at = context.get_current_parameters().get("created_at") or now()
    return quote_valid_until(created_at)


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    origin_postal_code: Mapped[str] = mapped_column(String(5))
    destination_postal_code: Mapped[str] = mapped_column(String(5))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    length_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    width_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Nulo en cotizaciones telefónicas: Comercial no registró la distancia.
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    zone: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default=QUOTE_SOURCE_WEB, server_default=QUOTE_SOURCE_WEB)
    external_ref: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    # Hasta cuándo se respeta el precio mostrado, aunque la tarifa cambie.
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_valid_until
    )

    lead = relationship("Lead", back_populates="quotes")
    options = relationship(
        "QuoteOption",
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteOption.price_mxn",
    )
