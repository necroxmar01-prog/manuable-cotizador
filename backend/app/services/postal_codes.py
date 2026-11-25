
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


class PostalCodeNotFoundError(Exception):
    """El código postal no existe o no está registrado en el servicio."""


class PostalCodeServiceError(Exception):
    """No fue posible consultar el servicio de códigos postales."""


# Las coordenadas de un CP no cambian: cachear las respuestas exitosas evita
# repetir llamadas lentas a Zippopotam (origen y destino suelen repetirse).
# Los errores no se cachean para no fijar una caída temporal del servicio.
_CACHE_MAX_ENTRIES = 5000
_coordinates_cache: dict[str, tuple[float, float]] = {}


def clear_postal_code_cache() -> None:
    _coordinates_cache.clear()


def get_postal_code_coordinates(
    postal_code: str,
) -> tuple[float, float]:
    """Obtiene latitud y longitud de un código postal mexicano."""

    if not isinstance(postal_code, str):
        raise ValueError(
            "El código postal debe contener exactamente cinco dígitos."
        )

    postal_code = re.sub(r"\s+", "", postal_code)

    if not re.fullmatch(r"\d{5}", postal_code):
        raise ValueError(
            "El código postal debe contener exactamente cinco dígitos."
        )

    cached = _coordinates_cache.get(postal_code)
    if cached is not None:
        return cached

    url = f"https://api.zippopotam.us/mx/{postal_code}"

    try:
        with urlopen(url, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        if error.code == 404:
            raise PostalCodeNotFoundError(
                f"No encontramos el código postal {postal_code}."
            ) from error

        raise PostalCodeServiceError(
            "El servicio de códigos postales no está disponible."
        ) from error

    except (URLError, TimeoutError, OSError) as error:
        raise PostalCodeServiceError(
            "No fue posible conectar con el servicio de códigos postales."
        ) from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PostalCodeServiceError(
            "El servicio devolvió una respuesta inválida."
        ) from error

    try:
        place = data["places"][0]
        latitude = float(place["latitude"])
        longitude = float(place["longitude"])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise PostalCodeServiceError(
            "No fue posible interpretar las coordenadas del código postal."
        ) from error

    if len(_coordinates_cache) >= _CACHE_MAX_ENTRIES:
        _coordinates_cache.clear()
    _coordinates_cache[postal_code] = (latitude, longitude)
    return latitude, longitude
