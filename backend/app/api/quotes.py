
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models import Lead, Quote, QuoteOption
from app.schemas.quote import QuoteRequest, QuoteResponse
from app.services.geography import calculate_distance_km, determine_zone
from app.services.postal_codes import (
    PostalCodeNotFoundError,
    PostalCodeServiceError,
    get_postal_code_coordinates,
)
from app.services.pricing import get_available_tariffs


router = APIRouter(prefix="/api/quotes", tags=["Quotes"])


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote(
    request: QuoteRequest,
    db: Session = Depends(get_db),
) -> Quote:
    """Calcula una cotización y registra el lead correspondiente."""

    try:
        origin_lat, origin_lon = get_postal_code_coordinates(
            request.origin_postal_code
        )
        destination_lat, destination_lon = get_postal_code_coordinates(
            request.destination_postal_code
        )

    except PostalCodeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except PostalCodeServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    distance = calculate_distance_km(
        origin_lat,
        origin_lon,
        destination_lat,
        destination_lon,
    )
    zone = determine_zone(distance)

    tariffs = get_available_tariffs(
        db=db,
        zone=zone,
        weight_kg=request.weight_kg,
    )

    lead = Lead(email=request.email)

    quote = Quote(
        origin_postal_code=request.origin_postal_code,
        destination_postal_code=request.destination_postal_code,
        weight_kg=request.weight_kg,
        distance_km=Decimal(str(distance)).quantize(Decimal("0.01")),
        zone=zone,
        lead=lead,
    )

    quote.options = [
        QuoteOption(
            carrier_name=tariff.carrier.name,
            service_type=tariff.carrier.service_type,
            price_mxn=tariff.price_mxn,
            delivery_days_min=tariff.delivery_days_min,
            delivery_days_max=tariff.delivery_days_max,
        )
        for tariff in tariffs
    ]

    try:
        db.add(quote)
        db.commit()
        db.refresh(quote)

    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible guardar la cotización.",
        ) from error

    return quote
