"""Fase 2 de punta a punta con los CSV reales de `datos/` (sin red)."""

import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.importers.sync import sync_data
from app.models import ImportBatch, ImportRecord, Quote, QuoteOption, Tariff
from app.services.pricing import Package, price_package

HERE = Path(__file__).resolve()
CANDIDATES = [HERE.parents[1] / "datos", HERE.parents[2] / "datos"]
DATA_DIR = next((p for p in CANDIDATES if (p / "tarifas.csv").exists()), None)

pytestmark = pytest.mark.skipif(DATA_DIR is None, reason="no se encontró la carpeta datos/")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def data_dir(tmp_path):
    target = tmp_path / "datos"
    shutil.copytree(DATA_DIR, target)
    return target


def batch(db, name):
    return db.scalar(select(ImportBatch).where(ImportBatch.source_file == name))


def test_sync_loads_all_sources(db, data_dir):
    sync_data(db, data_dir)

    dhl_v2 = batch(db, "tarifas_dhl_v2.csv")
    assert (dhl_v2.accepted_rows, dhl_v2.rejected_rows) == (24, 0)

    v1 = batch(db, "tarifas.csv")
    assert v1.quarantined_rows == 3
    quarantined = sorted(
        db.scalars(select(Tariff.price_mxn).where(Tariff.active.is_(False))).all()
    )
    assert quarantined == [Decimal("10.40"), Decimal("42237.00"), Decimal("217672.00")]

    historical = batch(db, "cotizaciones_historicas.csv")
    assert historical.rejected_rows == 0
    assert db.scalar(select(func.count()).select_from(Quote).where(Quote.source == "telefono")) == 40

    rules = batch(db, "reglas_peso.csv")
    assert rules.accepted_rows == 6


def test_sync_is_idempotent(db, data_dir):
    sync_data(db, data_dir)
    tariffs = db.scalar(select(func.count()).select_from(Tariff))
    quotes = db.scalar(select(func.count()).select_from(Quote))

    log = sync_data(db, data_dir)

    assert not any(": {" in line for line in log)  # ningún archivo se volvió a importar
    assert db.scalar(select(func.count()).select_from(Tariff)) == tariffs
    assert db.scalar(select(func.count()).select_from(Quote)) == quotes


def test_next_tariff_change_is_a_new_file_not_code(db, data_dir):
    sync_data(db, data_dir)
    (data_dir / "tarifas_estafeta_2027.csv").write_text(
        "paqueteria,zona,peso_min_kg,peso_max_kg,precio_mxn,dias_entrega,vigencia_desde\n"
        "Estafeta,4,0,1,250.00,6,2027-01-01\n",
        encoding="utf-8",
    )

    sync_data(db, data_dir)

    before = price_package(db, 4, Package(Decimal("0.5")), date(2026, 12, 31))
    after = price_package(db, 4, Package(Decimal("0.5")), date(2027, 1, 1))
    estafeta = lambda r: [o.tariff.price_mxn for o in r.options if o.tariff.carrier.name == "Estafeta"]
    assert estafeta(before) == [Decimal("232.48")]
    assert estafeta(after) == [Decimal("250.00")]


def test_dhl_switches_tariff_and_weight_method_on_december_first(db, data_dir):
    sync_data(db, data_dir)
    box = Package(Decimal("2"), Decimal("40"), Decimal("30"), Decimal("30"))  # 7.2 kg vol.

    nov = price_package(db, 4, box, date(2026, 11, 30))
    dec = price_package(db, 4, box, date(2026, 12, 1))

    dhl = lambda r: [(o.tariff.price_mxn, o.billable_weight_kg) for o in r.options if o.tariff.carrier.name == "DHL"]
    assert dhl(nov) == []  # DHL v1 no tiene rango 1-3 kg en zona 4
    assert dhl(dec) == [(Decimal("1381.86"), Decimal("7.200"))]


def test_historical_quotes_keep_promised_price_and_validity(db, data_dir):
    sync_data(db, data_dir)

    quote = db.scalar(select(Quote).where(Quote.external_ref == "COT-0003"))
    option = quote.options[0]

    assert quote.destination_postal_code == "06600"  # conserva el 0 inicial
    assert (option.carrier_name, option.price_mxn) == ("Estafeta", Decimal("422.37"))
    assert quote.valid_until.date() == date(2026, 11, 14)  # 15 oct + 30 días

    record = db.scalar(
        select(ImportRecord)
        .join(ImportBatch)
        .where(ImportBatch.kind == "historical_quotes", ImportRecord.row_number == 4)
    )
    # La tarifa de 42237.00 está en cuarentena: se avisa, no se cambia el precio.
    assert any("no hay tarifa vigente" in m for m in record.messages)


def test_legacy_phase1_batch_is_not_reimported(db, data_dir):
    from app.importers.tariffs import import_carriers, import_tariffs

    import_carriers(db, data_dir / "paqueterias.csv")
    import_tariffs(db, data_dir / "tarifas.csv")
    legacy = batch(db, "tarifas.csv")
    legacy.file_sha256 = None  # así quedaban los lotes de fase 1
    db.flush()
    tariffs = db.scalar(select(func.count()).select_from(Tariff))

    sync_data(db, data_dir)

    v1_tariffs = db.scalar(select(func.count()).select_from(Tariff).where(Tariff.source_file == "tarifas.csv"))
    assert v1_tariffs == tariffs
    assert legacy.file_sha256 is not None


def test_saved_quote_options_are_snapshots(db, data_dir):
    sync_data(db, data_dir)
    option = db.scalar(select(QuoteOption).limit(1))
    price = option.price_mxn

    for t in db.scalars(select(Tariff)).all():
        t.price_mxn = Decimal("1.00")
    db.flush()
    db.refresh(option)

    assert option.price_mxn == price
