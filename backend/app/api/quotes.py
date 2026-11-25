from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.clock import business_date, now, quote_valid_until
from app.db.dependencies import get_db
from app.models import Lead, Quote, QuoteOption
from app.models.quote import QUOTE_SOURCE_WEB
from app.schemas.quote import QuoteRequest, QuoteResponse
from app.services.geography import calculate_distance_km, determine_zone
from app.services.postal_codes import (
    PostalCodeNotFoundError,
    PostalCodeServiceError,
    get_postal_code_coordinates,
)
from app.services.pricing import Package, price_package


router = APIRouter(prefix="/api/quotes", tags=["Quotes"])


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote(
    request: QuoteRequest,
    db: Session = Depends(get_db),
) -> QuoteResponse:
    """Calcula una cotización, registra el lead y congela el precio 30 días."""

    try:
        origin_lat, origin_lon = get_postal_code_coordinates(request.origin_postal_code)
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

    distance = calculate_distance_km(origin_lat, origin_lon, destination_lat, destination_lon)
    zone = determine_zone(distance)

    created_at = now()
    package = Package(
        weight_kg=request.weight_kg,
        length_cm=request.length_cm,
        width_cm=request.width_cm,
        height_cm=request.height_cm,
    )
    pricing = price_package(db=db, zone=zone, package=package, quote_date=business_date(created_at))

    quote = Quote(
        origin_postal_code=request.origin_postal_code,
        destination_postal_code=request.destination_postal_code,
        weight_kg=request.weight_kg,
        length_cm=request.length_cm,
        width_cm=request.width_cm,
        height_cm=request.height_cm,
        distance_km=Decimal(str(distance)).quantize(Decimal("0.01")),
        zone=zone,
        source=QUOTE_SOURCE_WEB,
        created_at=created_at,
        valid_until=quote_valid_until(created_at),
        lead=Lead(email=request.email, created_at=created_at),
    )

    # Foto del precio mostrado: no se recalcula aunque la tarifa cambie.
    quote.options = [
        QuoteOption(
            carrier_name=option.tariff.carrier.name,
            service_type=option.tariff.carrier.service_type,
            price_mxn=option.tariff.price_mxn,
            delivery_days_min=option.tariff.delivery_days_min,
            delivery_days_max=option.tariff.delivery_days_max,
            billable_weight_kg=option.billable_weight_kg,
            weight_method=option.weight_method,
            tariff_id=option.tariff.id,
        )
        for option in pricing.options
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

    response = QuoteResponse.model_validate(quote)
    response.notices = pricing.notices
    return response
