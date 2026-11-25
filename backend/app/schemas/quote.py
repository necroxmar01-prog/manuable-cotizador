
import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuoteRequest(BaseModel):
    """Datos necesarios para solicitar una cotización."""

    origin_postal_code: str = Field(min_length=5, max_length=5)
    destination_postal_code: str = Field(min_length=5, max_length=5)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    email: str = Field(min_length=3, max_length=254)

    @field_validator(
        "origin_postal_code",
        "destination_postal_code",
        mode="before"
    )
    @classmethod
    def strip_postal_code(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("origin_postal_code", "destination_postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        if not re.fullmatch(r"\d{5}", value):
            raise ValueError(
                "El código postal debe contener exactamente cinco dígitos."
            )
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Ingresa un correo electrónico válido.")

        return value


class QuoteOptionResponse(BaseModel):
    """Una opción de paquetería disponible."""

    model_config = ConfigDict(from_attributes=True)

    carrier_name: str
    service_type: str
    price_mxn: Decimal
    delivery_days_min: int
    delivery_days_max: int


class QuoteResponse(BaseModel):
    """Resultado de una cotización."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    origin_postal_code: str
    destination_postal_code: str
    weight_kg: Decimal
    distance_km: Decimal
    zone: int
    options: list[QuoteOptionResponse]
