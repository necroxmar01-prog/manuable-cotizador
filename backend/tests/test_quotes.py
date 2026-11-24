
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import quotes as quotes_api
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import Carrier, Lead, Quote, Tariff
from app.services.postal_codes import (
    PostalCodeNotFoundError,
    PostalCodeServiceError,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def add_tariff(db: Session) -> None:
    carrier = Carrier(
        external_code="CARR-DHL",
        name="DHL",
        service_type="aéreo",
        active=True,
    )
    db.add(carrier)
    db.flush()

    tariff = Tariff(
        carrier_id=carrier.id,
        zone=3,
        weight_min_kg=Decimal("1.000"),
        weight_max_kg=Decimal("10.000"),
        price_mxn=Decimal("250.00"),
        delivery_days_min=3,
        delivery_days_max=5,
        valid_from=date(2026, 1, 1),
        source_file="test.csv",
        source_row=1,
        fingerprint="quote-test-fingerprint",
    )
    db.add(tariff)
    db.commit()


def mock_postal_coordinates(monkeypatch):
    def fake_coordinates(postal_code: str):
        coordinates = {
            "06600": (19.4326, -99.1332),
            "64000": (25.6866, -100.3161),
        }
        return coordinates[postal_code]

    monkeypatch.setattr(
        quotes_api,
        "get_postal_code_coordinates",
        fake_coordinates,
    )


def quote_payload():
    return {
        "origin_postal_code": "06600",
        "destination_postal_code": "64000",
        "weight_kg": "5.000",
        "email": "  CLIENTE@EXAMPLE.COM  ",
    }


def test_create_quote_success(client, db_session, monkeypatch):
    add_tariff(db_session)
    mock_postal_coordinates(monkeypatch)

    response = client.post("/api/quotes", json=quote_payload())

    assert response.status_code == 201

    data = response.json()
    assert data["origin_postal_code"] == "06600"
    assert data["destination_postal_code"] == "64000"
    assert data["zone"] == 3
    assert len(data["options"]) == 1
    assert data["options"][0]["carrier_name"] == "DHL"
    assert data["options"][0]["price_mxn"] == "250.00"

    lead = db_session.scalar(select(Lead))
    quote = db_session.scalar(select(Quote))

    assert lead.email == "cliente@example.com"
    assert quote.lead_id == lead.id


def test_returns_404_when_postal_code_does_not_exist(
    client,
    db_session,
    monkeypatch,
):
    def missing_postal_code(postal_code: str):
        raise PostalCodeNotFoundError("Código postal no encontrado.")

    monkeypatch.setattr(
        quotes_api,
        "get_postal_code_coordinates",
        missing_postal_code,
    )

    response = client.post("/api/quotes", json=quote_payload())

    assert response.status_code == 404
    assert response.json()["detail"] == "Código postal no encontrado."
    assert db_session.scalar(select(Lead)) is None


def test_returns_503_when_postal_service_is_unavailable(
    client,
    db_session,
    monkeypatch,
):
    def unavailable_service(postal_code: str):
        raise PostalCodeServiceError("Servicio no disponible.")

    monkeypatch.setattr(
        quotes_api,
        "get_postal_code_coordinates",
        unavailable_service,
    )

    response = client.post("/api/quotes", json=quote_payload())

    assert response.status_code == 503
    assert response.json()["detail"] == "Servicio no disponible."
    assert db_session.scalar(select(Lead)) is None


def test_creates_quote_without_options_when_no_tariff_matches(
    client,
    db_session,
    monkeypatch,
):
    mock_postal_coordinates(monkeypatch)

    response = client.post("/api/quotes", json=quote_payload())

    assert response.status_code == 201
    assert response.json()["options"] == []
    assert db_session.scalar(select(Lead)) is not None
    assert db_session.scalar(select(Quote)) is not None


def test_rejects_invalid_quote_data(client, monkeypatch):
    def postal_service_must_not_be_called(postal_code: str):
        pytest.fail("No debería consultar el servicio postal.")

    monkeypatch.setattr(
        quotes_api,
        "get_postal_code_coordinates",
        postal_service_must_not_be_called,
    )

    payload = quote_payload()
    payload["origin_postal_code"] = "123"
    payload["weight_kg"] = "-5"

    response = client.post("/api/quotes", json=payload)

    assert response.status_code == 422
