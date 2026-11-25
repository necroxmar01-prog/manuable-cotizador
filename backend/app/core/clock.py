"""Reglas de tiempo del negocio.

Las vigencias de tarifas y de cotizaciones se expresan en fechas de calendario
de Monterrey; el contenedor corre en UTC, así que nunca usamos date.today().
"""

import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("America/Monterrey")
QUOTE_VALIDITY_DAYS = 30


def simulated_now() -> datetime | None:
    """Fecha fija para demos y pruebas manuales (variable FECHA_SIMULADA).

    Permite mostrar hoy cómo cotizará el sistema el 1 de diciembre. Nunca
    debe definirse en producción.
    """
    raw = os.getenv("FECHA_SIMULADA", "").strip()
    if not raw:
        return None
    moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=BUSINESS_TZ)
    return moment.astimezone(BUSINESS_TZ)


def now() -> datetime:
    return simulated_now() or datetime.now(BUSINESS_TZ)


def business_date(moment: datetime | None = None) -> date:
    """Fecha de calendario en Monterrey para un instante (por defecto, ahora)."""
    moment = moment or now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(BUSINESS_TZ).date()


def quote_valid_until(created_at: datetime) -> datetime:
    """Una cotización se respeta hasta el fin del día 30 después de emitirse."""
    last_day = business_date(created_at) + timedelta(days=QUOTE_VALIDITY_DAYS)
    return datetime.combine(last_day, time(23, 59, 59), tzinfo=BUSINESS_TZ)
