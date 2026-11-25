import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_DIMENSION_CM = Decimal("300")


def normalize_postal_code(value: object) -> object:
    """Quita cualquier espacio (incluidos los de copiar/pegar) y valida con
    mensajes que orienten a la persona en los errores más comunes."""

    if not isinstance(value, str):
        return value
    cleaned = re.sub(r"\s+", "", value)
    if re.fullmatch(r"\d{5}", cleaned):
        return cleaned
    if re.search(r"[^\W\d_]", cleaned):
        raise ValueError(
            "Escribe el código postal de 5 dígitos, no el nombre de la ciudad o colonia."
        )
    if re.fullmatch(r"\d{4}", cleaned):
        raise ValueError(
            "El código postal debe tener 5 dígitos. Si empieza con 0, inclúyelo (ej. 06600)."
        )
    raise ValueError("El código postal debe contener exactamente cinco dígitos.")


class QuoteRequest(BaseModel):
    """Datos necesarios para solicitar una cotización."""

    origin_postal_code: str
    destination_postal_code: str
    weight_kg: Decimal = Field(gt=0, le=1000, max_digits=10, decimal_places=3)
    email: str = Field(min_length=3, max_length=254)
    # Opcionales para no romper integraciones de fase 1, pero necesarias
    # para cotizar paqueterías que cobran por peso volumétrico.
    length_cm: Decimal | None = Field(default=None, gt=0, le=MAX_DIMENSION_CM, decimal_places=2)
    width_cm: Decimal | None = Field(default=None, gt=0, le=MAX_DIMENSION_CM, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, gt=0, le=MAX_DIMENSION_CM, decimal_places=2)

    @field_validator("origin_postal_code", "destination_postal_code", mode="before")
    @classmethod
    def validate_postal_code(cls, value: object) -> object:
        return normalize_postal_code(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Ingresa un correo electrónico válido.")

        return value

    @model_validator(mode="after")
    def dimensions_all_or_none(self) -> "QuoteRequest":
        dims = (self.length_cm, self.width_cm, self.height_cm)
        if any(d is not None for d in dims) and not all(d is not None for d in dims):
            raise ValueError("Indica largo, ancho y alto del paquete, o ninguno.")
        return self


class QuoteOptionResponse(BaseModel):
    """Una opción de paquetería disponible."""

    model_config = ConfigDict(from_attributes=True)

    carrier_name: str
    service_type: str
    price_mxn: Decimal
    delivery_days_min: int | None
    delivery_days_max: int | None
    billable_weight_kg: Decimal | None = None
    weight_method: str | None = None


class QuoteResponse(BaseModel):
    """Resultado de una cotización."""

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
    created_at: datetime
    valid_until: datetime
    options: list[QuoteOptionResponse]
    notices: list[str] = []
