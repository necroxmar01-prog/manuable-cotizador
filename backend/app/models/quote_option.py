
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuoteOption(Base):
    __tablename__ = "quote_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="CASCADE"),
        index=True,
    )
    carrier_name: Mapped[str] = mapped_column(String(80))
    service_type: Mapped[str] = mapped_column(String(40))
    price_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_days_min: Mapped[int] = mapped_column(Integer)
    delivery_days_max: Mapped[int] = mapped_column(Integer)

    quote = relationship("Quote", back_populates="options")
