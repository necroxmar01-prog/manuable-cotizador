
import math


def calculate_distance_km(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
) -> float:
    """Calcula la distancia geográfica entre dos puntos usando Haversine."""

    coordinates = (
        origin_lat,
        origin_lon,
        destination_lat,
        destination_lon,
    )

    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("Las coordenadas deben ser números finitos.")

    if not -90 <= origin_lat <= 90:
        raise ValueError("Latitud de origen fuera de rango.")

    if not -90 <= destination_lat <= 90:
        raise ValueError("Latitud de destino fuera de rango.")

    if not -180 <= origin_lon <= 180:
        raise ValueError("Longitud de origen fuera de rango.")

    if not -180 <= destination_lon <= 180:
        raise ValueError("Longitud de destino fuera de rango.")

    earth_radius_km = 6371.0

    lat1 = math.radians(origin_lat)
    lat2 = math.radians(destination_lat)
    delta_lat = math.radians(destination_lat - origin_lat)
    delta_lon = math.radians(destination_lon - origin_lon)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    # Evita errores numéricos por redondeo.
    a = min(1.0, max(0.0, a))

    central_angle = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1.0 - a),
    )

    return earth_radius_km * central_angle


def determine_zone(distance_km: float) -> int:
    """Determina la zona tarifaria según la distancia en kilómetros."""

    if not math.isfinite(distance_km) or distance_km < 0:
        raise ValueError("La distancia debe ser un número válido no negativo.")

    if distance_km <= 100:
        return 1

    if distance_km <= 500:
        return 2

    if distance_km <= 1000:
        return 3

    return 4
