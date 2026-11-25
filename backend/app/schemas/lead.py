from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.quote import QuoteOptionResponse


class LeadQuoteResponse(BaseModel):
    """Información de una cotización asociada a un lead."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    origin_postal_code: str
    destination_postal_code: str
    weight_kg: Decimal
    distance_km: Decimal
    zone: int
    created_at: datetime
    options: list[QuoteOptionResponse]


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