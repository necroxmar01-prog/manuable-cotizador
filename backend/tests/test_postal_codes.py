
import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from app.services.postal_codes import (
    PostalCodeNotFoundError,
    PostalCodeServiceError,
    get_postal_code_coordinates,
)


def test_returns_coordinates(monkeypatch):
    response_data = {
        "places": [
            {
                "latitude": "19.4326",
                "longitude": "-99.1332",
            }
        ]
    }

    def fake_urlopen(url, timeout):
        assert url.endswith("/mx/06600")
        assert timeout == 5
        return BytesIO(json.dumps(response_data).encode("utf-8"))

    monkeypatch.setattr(
        "app.services.postal_codes.urlopen",
        fake_urlopen,
    )

    coordinates = get_postal_code_coordinates("06600")

    assert coordinates == (19.4326, -99.1332)


@pytest.mark.parametrize(
    "postal_code",
    ["6600", "123456", "ABCDE", "", " 06600", None],
)
def test_rejects_invalid_postal_codes(postal_code):
    with pytest.raises(ValueError):
        get_postal_code_coordinates(postal_code)


def test_postal_code_not_found(monkeypatch):
    def fake_urlopen(url, timeout):
        raise HTTPError(
            url,
            404,
            "Not Found",
            None,
            None,
        )

    monkeypatch.setattr(
        "app.services.postal_codes.urlopen",
        fake_urlopen,
    )

    with pytest.raises(PostalCodeNotFoundError):
        get_postal_code_coordinates("99999")


def test_connection_error(monkeypatch):
    def fake_urlopen(url, timeout):
        raise URLError("Connection refused")

    monkeypatch.setattr(
        "app.services.postal_codes.urlopen",
        fake_urlopen,
    )

    with pytest.raises(PostalCodeServiceError):
        get_postal_code_coordinates("06600")


def test_invalid_api_response(monkeypatch):
    def fake_urlopen(url, timeout):
        return BytesIO(b"not valid json")

    monkeypatch.setattr(
        "app.services.postal_codes.urlopen",
        fake_urlopen,
    )

    with pytest.raises(PostalCodeServiceError):
        get_postal_code_coordinates("06600")


def test_missing_coordinates(monkeypatch):
    response_data = {"places": [{}]}

    def fake_urlopen(url, timeout):
        return BytesIO(json.dumps(response_data).encode("utf-8"))

    monkeypatch.setattr(
        "app.services.postal_codes.urlopen",
        fake_urlopen,
    )

    with pytest.raises(PostalCodeServiceError):
        get_postal_code_coordinates("06600")
