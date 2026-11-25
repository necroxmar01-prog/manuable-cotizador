"""Fase 2 vía API: vigencia de 30 días, hora de Monterrey, volumétrico y métricas."""

import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import metrics as metrics_api
from app.api import quotes as quotes_api
from app.core.clock import BUSINESS_TZ
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import Carrier, CarrierPricingRule, Lead, Quote, QuoteOption, Tariff

COORDS = {"06600": (19.385, -99.165), "64000": (25.6866, -100.3161)}  # zona 3


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setattr(quotes_api, "get_postal_code_coordinates", lambda cp: COORDS[cp])

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth():
    return {"Authorization": "Basic " + base64.b64encode(b"admin:secret").decode()}


def freeze(monkeypatch, moment: datetime):
    monkeypatch.setattr(quotes_api, "now", lambda: moment.astimezone(BUSINESS_TZ))


def seed_dhl(db):
    dhl = Carrier(external_code="CARR-01", name="DHL", service_type="aéreo", active=True)
    db.add(dhl)
    db.flush()
    for i, (lo, hi, price, since) in enumerate([
        ("0", "5", "300.00", date(2026, 1, 1)),
        ("5", "10", "1074.84", date(2026, 1, 1)),
        ("0", "5", "751.58", date(2026, 12, 1)),
        ("5", "10", "1171.58", date(2026, 12, 1)),
    ]):
        db.add(Tariff(
            carrier_id=dhl.id, zone=3, weight_min_kg=Decimal(lo), weight_max_kg=Decimal(hi),
            price_mxn=Decimal(price), delivery_days_min=3, delivery_days_max=3,
            valid_from=since, source_file="t.csv", source_row=i, fingerprint=f"fp{i}",
        ))
    db.add(CarrierPricingRule(carrier_id=dhl.id, weight_method="volumetrico",
                              volumetric_divisor=5000, valid_from=date(2026, 12, 1)))
    db.commit()


def payload(**extra):
    data = {"origin_postal_code": "06600", "destination_postal_code": "64000",
            "weight_kg": "2", "email": "ana@tienda.mx"}
    data.update(extra)
    return data


def test_quote_shows_valid_until_30_days(client, db, monkeypatch):
    seed_dhl(db)
    freeze(monkeypatch, datetime(2026, 11, 20, 10, 0, tzinfo=BUSINESS_TZ))

    body = client.post("/api/quotes", json=payload()).json()

    assert body["valid_until"].startswith("2026-12-20T23:59:59")
    assert body["options"][0]["price_mxn"] == "300.00"


def test_new_tariffs_start_at_midnight_monterrey_not_utc(client, db, monkeypatch):
    """30 nov 20:00 en Monterrey ya es 1 dic en UTC: debe seguir la tarifa vieja."""
    seed_dhl(db)
    freeze(monkeypatch, datetime(2026, 12, 1, 2, 0, tzinfo=timezone.utc))

    body = client.post("/api/quotes", json=payload()).json()

    assert body["options"][0]["price_mxn"] == "300.00"
    assert body["options"][0]["weight_method"] == "real"


def test_volumetric_price_from_december(client, db, monkeypatch):
    seed_dhl(db)
    freeze(monkeypatch, datetime(2026, 12, 1, 9, 0, tzinfo=BUSINESS_TZ))

    body = client.post(
        "/api/quotes", json=payload(length_cm="40", width_cm="30", height_cm="30")
    ).json()

    option = body["options"][0]
    assert option["price_mxn"] == "1171.58"
    assert option["billable_weight_kg"] == "7.200"
    assert option["weight_method"] == "volumetrico"


def test_missing_dimensions_returns_notice(client, db, monkeypatch):
    seed_dhl(db)
    freeze(monkeypatch, datetime(2026, 12, 2, 9, 0, tzinfo=BUSINESS_TZ))

    body = client.post("/api/quotes", json=payload()).json()

    assert body["options"] == []
    assert "largo, ancho y alto" in body["notices"][0]


def test_partial_dimensions_are_rejected(client):
    response = client.post("/api/quotes", json=payload(length_cm="40"))

    assert response.status_code == 422
    assert "largo, ancho y alto" in response.json()["detail"]


def test_quote_created_before_change_keeps_its_price(client, db, monkeypatch):
    seed_dhl(db)
    freeze(monkeypatch, datetime(2026, 11, 25, 9, 0, tzinfo=BUSINESS_TZ))
    quote_id = client.post("/api/quotes", json=payload()).json()["id"]

    freeze(monkeypatch, datetime(2026, 12, 5, 9, 0, tzinfo=BUSINESS_TZ))
    client.post("/api/quotes", json=payload(length_cm="10", width_cm="10", height_cm="10"))

    leads = client.get("/api/leads", headers=auth()).json()["items"]
    old = next(q for lead in leads for q in lead["quotes"] if q["id"] == quote_id)
    assert old["options"][0]["price_mxn"] == "300.00"
    assert old["price_guaranteed"] is True  # vence el 25 de diciembre


def add_quote(db, created_at, n_options, source="web"):
    quote = Quote(
        origin_postal_code="06600", destination_postal_code="64000", weight_kg=Decimal("1"),
        distance_km=Decimal("700"), zone=3, source=source, created_at=created_at,
        lead=Lead(email="x@y.mx", created_at=created_at),
        options=[
            QuoteOption(carrier_name="DHL", service_type="aéreo", price_mxn=Decimal("100"),
                        delivery_days_min=1, delivery_days_max=1)
            for _ in range(n_options)
        ],
    )
    db.add(quote)
    db.commit()


def test_metrics_count_per_monterrey_day_and_without_options(client, db, monkeypatch):
    today = datetime(2026, 11, 20, 12, 0, tzinfo=BUSINESS_TZ)
    monkeypatch.setattr(metrics_api, "business_date", lambda moment=None: (
        today.date() if moment is None else moment.astimezone(BUSINESS_TZ).date()
        if moment.tzinfo else moment.date()
    ))
    add_quote(db, today, 2)
    add_quote(db, today, 0)
    add_quote(db, today - timedelta(days=1), 0)
    add_quote(db, today, 1, source="telefono")  # no cuenta: no es uso del cotizador

    body = client.get("/api/metrics/quotes?days=7", headers=auth()).json()

    assert body["total_quotes"] == 3
    assert body["total_without_options"] == 2
    assert body["daily"][0] == {"date": "2026-11-20", "quotes": 2, "without_options": 1}
    assert body["daily"][1] == {"date": "2026-11-19", "quotes": 1, "without_options": 1}
    assert len(body["daily"]) == 7


def test_metrics_require_admin(client):
    assert client.get("/api/metrics/quotes").status_code == 401


def test_leads_can_be_filtered_by_email(client, db):
    add_quote(db, datetime(2026, 11, 20, tzinfo=BUSINESS_TZ), 1)
    db.add(Lead(email="otra@cliente.mx"))
    db.commit()

    body = client.get("/api/leads?email=OTRA", headers=auth()).json()

    assert body["total"] == 1
    assert body["items"][0]["email"] == "otra@cliente.mx"
