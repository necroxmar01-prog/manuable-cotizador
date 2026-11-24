
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id"),
        index=True,
    )
    origin_postal_code: Mapped[str] = mapped_column(String(5))
    destination_postal_code: Mapped[str] = mapped_column(String(5))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    zone: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    lead = relationship("Lead", back_populates="quotes")
    options = relationship(
        "QuoteOption",
        back_populates="quote",
        cascade="all, delete-orphan",
    )
