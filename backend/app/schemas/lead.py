from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.clock import now
from app.schemas.quote import QuoteOptionResponse


class LeadQuoteResponse(BaseModel):
    """Información de una cotización asociada a un lead."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    origin_postal_code: str
    destination_postal_code: str
    weight_kg: Decimal
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    distance_km: Decimal | None
    zone: int
    source: str
    external_ref: str | None = None
    created_at: datetime
    valid_until: datetime
    options: list[QuoteOptionResponse]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def price_guaranteed(self) -> bool:
        """True mientras se deba respetar el precio mostrado."""
        valid_until = self.valid_until
        if valid_until.tzinfo is None:  # SQLite en pruebas no guarda zona
            return valid_until >= now().replace(tzinfo=None)
        return valid_until >= now()


class LeadResponse(BaseModel):
    """Información de un lead y su historial de cotizaciones."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
    quotes: list[LeadQuoteResponse]


class LeadListResponse(BaseModel):
    """Resultado paginado de la consulta de leads."""

    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DailyQuoteMetrics(BaseModel):
    date: str
    quotes: int
    without_options: int


class QuoteMetricsResponse(BaseModel):
    """Uso del cotizador público (excluye cotizaciones telefónicas)."""

    days: int
    total_quotes: int
    total_without_options: int
    daily: list[DailyQuoteMetrics]
