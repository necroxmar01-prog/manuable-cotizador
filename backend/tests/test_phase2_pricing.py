"""Fase 2: tarifario vigente por paquetería, peso volumétrico y cuarentena."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.importers.tariffs import quarantine_price_outliers
from app.models import Carrier, CarrierPricingRule, Tariff
from app.services.pricing import Package, billable_weight, price_package

BEFORE = date(2026, 11, 30)
AFTER = date(2026, 12, 1)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def carrier(db, name):
    c = Carrier(external_code=f"C-{name}", name=name, service_type="aéreo", active=True)
    db.add(c)
    db.flush()
    return c


_seq = iter(range(1, 10_000))


def tariff(db, c, lo, hi, price, valid_from=date(2026, 1, 1), zone=2, active=True):
    t = Tariff(
        carrier_id=c.id, zone=zone,
        weight_min_kg=Decimal(lo), weight_max_kg=Decimal(hi), price_mxn=Decimal(price),
        delivery_days_min=2, delivery_days_max=2, valid_from=valid_from,
        source_file="t.csv", source_row=1, fingerprint=f"fp-{next(_seq)}", active=active,
    )
    db.add(t)
    db.flush()
    return t


def rule(db, c, method, valid_from, divisor=None):
    db.add(CarrierPricingRule(carrier_id=c.id, weight_method=method,
                              volumetric_divisor=divisor, valid_from=valid_from))
    db.flush()


def prices(result):
    return [(o.tariff.carrier.name, o.tariff.price_mxn, o.billable_weight_kg) for o in result.options]


def test_boundary_weight_matches_a_single_range(db):
    """1 kg exacto caía en 0–1 y 1–3: la misma paquetería salía dos veces."""
    dhl = carrier(db, "DHL")
    tariff(db, dhl, "0", "1", "100")
    tariff(db, dhl, "1", "3", "200")

    result = price_package(db, 2, Package(Decimal("1")), BEFORE)

    assert prices(result) == [("DHL", Decimal("100.00"), Decimal("1"))]


def test_new_tariff_book_replaces_previous_one_from_its_start_date(db):
    """El rango 3–6 kg de v1 no existe en v2: no debe sobrevivir al cambio."""
    dhl = carrier(db, "DHL")
    tariff(db, dhl, "3", "6", "470")
    tariff(db, dhl, "5", "10", "961.29", valid_from=AFTER)

    assert prices(price_package(db, 2, Package(Decimal("5.5")), BEFORE)) == [
        ("DHL", Decimal("470.00"), Decimal("5.5"))
    ]
    assert prices(price_package(db, 2, Package(Decimal("5.5")), AFTER)) == [
        ("DHL", Decimal("961.29"), Decimal("5.5"))
    ]


def test_volumetric_weight_applies_only_from_rule_start_date(db):
    dhl = carrier(db, "DHL")
    tariff(db, dhl, "0", "5", "300")
    tariff(db, dhl, "5", "10", "600")
    rule(db, dhl, "real", date(2026, 1, 1))
    rule(db, dhl, "volumetrico", AFTER, divisor=5000)
    # 2 kg reales en una caja de 40x30x30 = 7.2 kg volumétricos
    box = Package(Decimal("2"), Decimal("40"), Decimal("30"), Decimal("30"))

    assert prices(price_package(db, 2, box, BEFORE)) == [("DHL", Decimal("300.00"), Decimal("2"))]
    assert prices(price_package(db, 2, box, AFTER)) == [("DHL", Decimal("600.00"), Decimal("7.200"))]


def test_real_weight_wins_when_heavier_than_volumetric(db):
    rule_obj = CarrierPricingRule(weight_method="volumetrico", volumetric_divisor=5000)
    small_heavy = Package(Decimal("8"), Decimal("10"), Decimal("10"), Decimal("10"))

    assert billable_weight(small_heavy, rule_obj) == (Decimal("8"), "volumetrico")


def test_carriers_without_volumetric_rule_keep_real_weight(db):
    estafeta = carrier(db, "Estafeta")
    tariff(db, estafeta, "0", "5", "250")
    rule(db, estafeta, "real", date(2026, 1, 1))
    box = Package(Decimal("2"), Decimal("40"), Decimal("30"), Decimal("30"))

    assert prices(price_package(db, 2, box, AFTER)) == [("Estafeta", Decimal("250.00"), Decimal("2"))]


def test_future_rule_change_needs_only_data(db):
    """Cuando Estafeta renueve: se agrega una regla con fecha, sin tocar código."""
    estafeta = carrier(db, "Estafeta")
    tariff(db, estafeta, "0", "5", "250")
    tariff(db, estafeta, "5", "10", "500")
    rule(db, estafeta, "real", date(2026, 1, 1))
    rule(db, estafeta, "volumetrico", date(2027, 3, 1), divisor=5000)
    box = Package(Decimal("2"), Decimal("40"), Decimal("30"), Decimal("30"))

    assert prices(price_package(db, 2, box, date(2027, 2, 28)))[0][1] == Decimal("250.00")
    assert prices(price_package(db, 2, box, date(2027, 3, 1)))[0][1] == Decimal("500.00")


def test_volumetric_carrier_without_dimensions_is_explained_not_guessed(db):
    dhl = carrier(db, "DHL")
    estafeta = carrier(db, "Estafeta")
    tariff(db, dhl, "0", "5", "300")
    tariff(db, estafeta, "0", "5", "250")
    rule(db, dhl, "volumetrico", AFTER, divisor=5000)

    result = price_package(db, 2, Package(Decimal("2")), AFTER)

    assert [name for name, *_ in prices(result)] == ["Estafeta"]
    assert "DHL" in result.notices[0]


def test_heavy_volumetric_package_beyond_tariffs_gets_no_option(db):
    dhl = carrier(db, "DHL")
    tariff(db, dhl, "20", "30", "2000")
    rule(db, dhl, "volumetrico", AFTER, divisor=5000)
    huge = Package(Decimal("1"), Decimal("100"), Decimal("100"), Decimal("100"))  # 200 kg vol.

    assert price_package(db, 2, huge, AFTER).options == []


def test_price_outliers_are_quarantined_and_not_quoted(db):
    """217672.00 donde el histórico muestra 2176.72: no se cotiza."""
    names = ["DHL", "Estafeta", "FedEx", "Redpack"]
    carriers = [carrier(db, n) for n in names]
    for c, price in zip(carriers, ["1183.00", "812.25", "1179.36", "217672.00"]):
        tariff(db, c, "10", "20", price, zone=4)

    quarantine_price_outliers(db)

    result = price_package(db, 4, Package(Decimal("15")), BEFORE)
    assert "Redpack" not in [name for name, *_ in prices(result)]
    flagged = db.query(Tariff).filter(Tariff.active.is_(False)).one()
    assert flagged.price_mxn == Decimal("217672.00")
    assert "atípico" in flagged.review_note


def test_quarantine_needs_enough_references(db):
    dhl = carrier(db, "DHL")
    tariff(db, dhl, "10", "20", "99999")
    tariff(db, dhl, "10", "20", "100", zone=3)

    quarantine_price_outliers(db)

    assert db.query(Tariff).filter(Tariff.active.is_(False)).count() == 0
