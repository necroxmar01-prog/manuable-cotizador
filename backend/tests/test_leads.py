import base64
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import Lead, Quote, QuoteOption


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
def client(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin-test")
    monkeypatch.setenv("ADMIN_PASSWORD", "password-test")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def admin_headers(username="admin-test", password="password-test"):
    credentials = f"{username}:{password}".encode("utf-8")
    encoded = base64.b64encode(credentials).decode("ascii")

    return {"Authorization": f"Basic {encoded}"}


def add_lead(db_session, email="cliente@example.com"):
    lead = Lead(email=email)
    quote = Quote(
        origin_postal_code="06600",
        destination_postal_code="64000",
        weight_kg=Decimal("5.000"),
        distance_km=Decimal("705.50"),
        zone=3,
        options=[
            QuoteOption(
                carrier_name="DHL",
                service_type="aereo",
                price_mxn=Decimal("250.00"),
                delivery_days_min=3,
                delivery_days_max=5,
            )
        ],
    )

    lead.quotes.append(quote)
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    return lead


def test_rejects_request_without_credentials(client):
    response = client.get("/api/leads")

    assert response.status_code == 401


def test_rejects_invalid_credentials(client):
    response = client.get(
        "/api/leads",
        headers=admin_headers(password="incorrecta"),
    )

    assert response.status_code == 401


def test_returns_leads_with_quotes_and_options(client, db_session):
    add_lead(db_session)

    response = client.get(
        "/api/leads",
        headers=admin_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["pages"] == 1

    lead = data["items"][0]
    assert lead["email"] == "cliente@example.com"
    assert len(lead["quotes"]) == 1

    quote = lead["quotes"][0]
    assert quote["origin_postal_code"] == "06600"
    assert quote["destination_postal_code"] == "64000"
    assert quote["zone"] == 3
    assert quote["options"][0]["carrier_name"] == "DHL"
    assert quote["options"][0]["price_mxn"] == "250.00"


def test_returns_empty_list_when_there_are_no_leads(client):
    response = client.get(
        "/api/leads",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "pages": 0,
    }


def test_supports_pagination(client, db_session):
    for index in range(3):
        add_lead(
            db_session,
            email=f"cliente{index}@example.com",
        )

    response = client.get(
        "/api/leads?page=2&page_size=2",
        headers=admin_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["pages"] == 2
    assert len(data["items"]) == 1


@pytest.mark.parametrize(
    "query",
    [
        "?page=0",
        "?page_size=0",
        "?page_size=101",
    ],
)
def test_rejects_invalid_pagination_parameters(client, query):
    response = client.get(
        f"/api/leads{query}",
        headers=admin_headers(),
    )

    assert response.status_code == 422

@pytest.mark.parametrize(
    "missing_setting",
    ["ADMIN_USERNAME", "ADMIN_PASSWORD"],
)
def test_returns_503_when_admin_credentials_are_not_configured(
    client,
    monkeypatch,
    missing_setting,
):
    monkeypatch.delenv(missing_setting, raising=False)

    response = client.get(
        "/api/leads",
        headers=admin_headers(),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "La autenticación administrativa no está configurada."
    )
