
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Carrier, Tariff
from app.services.pricing import get_available_tariffs


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def add_carrier(
    db: Session,
    name: str = "DHL",
    active: bool = True,
) -> Carrier:
    carrier = Carrier(
        external_code=f"CARR-{name}",
        name=name,
        service_type="aéreo",
        active=active,
    )
    db.add(carrier)
    db.flush()
    return carrier


def add_tariff(
    db: Session,
    carrier: Carrier,
    zone: int = 2,
    minimum: str = "1.000",
    maximum: str = "10.000",
    price: str = "250.00",
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
) -> Tariff:
    tariff = Tariff(
        carrier_id=carrier.id,
        zone=zone,
        weight_min_kg=Decimal(minimum),
        weight_max_kg=Decimal(maximum),
        price_mxn=Decimal(price),
        delivery_days_min=3,
        delivery_days_max=5,
        valid_from=valid_from,
        valid_to=valid_to,
        source_file="test.csv",
        source_row=1,
        fingerprint=f"fingerprint-{carrier.id}-{zone}-{price}-{valid_from}",
    )
    db.add(tariff)
    db.flush()
    return tariff


def test_returns_tariffs_matching_zone_and_weight(db_session):
    carrier = add_carrier(db_session)
    expected = add_tariff(db_session, carrier)

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 11, 24),
    )

    assert len(result) == 1
    assert result[0].id == expected.id
    assert result[0].carrier.name == "DHL"


def test_excludes_inactive_carriers(db_session):
    inactive = add_carrier(db_session, name="Redpack", active=False)
    add_tariff(db_session, inactive)

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 11, 24),
    )

    assert result == []


def test_excludes_tariffs_not_yet_valid(db_session):
    carrier = add_carrier(db_session)
    add_tariff(
        db_session,
        carrier,
        valid_from=date(2026, 12, 1),
    )

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 11, 24),
    )

    assert result == []


def test_returns_empty_when_no_tariff_matches(db_session):
    carrier = add_carrier(db_session)
    add_tariff(db_session, carrier, zone=3)

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 11, 24),
    )

    assert result == []


def test_orders_tariffs_by_price_ascending(db_session):
    dhl = add_carrier(db_session, name="DHL")
    fedex = add_carrier(db_session, name="FedEx")

    add_tariff(db_session, dhl, price="350.00")
    add_tariff(db_session, fedex, price="200.00")

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 11, 24),
    )

    assert [tariff.price_mxn for tariff in result] == [
        Decimal("200.00"),
        Decimal("350.00"),
    ]


@pytest.mark.parametrize(
    "weight",
    ["1.000", "10.000"],
)
def test_includes_exact_weight_range_boundaries(db_session, weight):
    carrier = add_carrier(db_session)
    expected = add_tariff(db_session, carrier)

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal(weight),
        quote_date=date(2026, 11, 24),
    )

    assert len(result) == 1
    assert result[0].id == expected.id


@pytest.mark.parametrize(
    "weight",
    ["0.999", "10.001"],
)
def test_excludes_weights_outside_tariff_range(db_session, weight):
    carrier = add_carrier(db_session)
    add_tariff(db_session, carrier)

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal(weight),
        quote_date=date(2026, 11, 24),
    )

    assert result == []

def test_includes_tariff_on_its_last_valid_day(db_session):
    carrier = add_carrier(db_session)
    expected = add_tariff(
        db_session,
        carrier,
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 11, 30),
    )

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 11, 30),
    )

    assert len(result) == 1
    assert result[0].id == expected.id


def test_excludes_tariff_after_its_last_valid_day(db_session):
    carrier = add_carrier(db_session)
    add_tariff(
        db_session,
        carrier,
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 11, 30),
    )

    result = get_available_tariffs(
        db_session,
        zone=2,
        weight_kg=Decimal("5.000"),
        quote_date=date(2026, 12, 1),
    )

    assert result == []