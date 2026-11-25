from datetime import date
from decimal import Decimal

import pytest

from app.importers.tariffs import (
    normalize_row,
    parse_carrier,
    parse_date,
    parse_price,
    parse_zone,
)


def valid_row(**overrides):
    row = {
        "paqueteria": "DHL ",
        "zona": "ZONA 3",
        "peso_min": "5000",
        "peso_max": "10000",
        "unidad": "g",
        "precio": "$1,137.24",
        "dias_entrega": "3-5",
        "vigencia_desde": "01/01/2026",
    }
    row.update(overrides)
    return row


def test_normalizes_carrier_zone_grams_price_and_date():
    tariff = normalize_row(valid_row())
    assert tariff.carrier_name == "DHL"
    assert tariff.zone == 3
    assert tariff.weight_min_kg == Decimal("5.000")
    assert tariff.weight_max_kg == Decimal("10.000")
    assert tariff.price_mxn == Decimal("1137.24")
    assert (tariff.delivery_days_min, tariff.delivery_days_max) == (3, 5)
    assert tariff.valid_from == date(2026, 1, 1)
    assert tariff.messages


def test_infers_grams_only_when_range_exceeds_30_and_unit_is_missing():
    tariff = normalize_row(valid_row(unidad="", peso_min="5000", peso_max="10000"))
    assert tariff.weight_min_kg == Decimal("5.000")
    assert any("gramos" in message for message in tariff.messages)


def test_rejects_ambiguous_missing_unit():
    with pytest.raises(ValueError, match="no inferible"):
        normalize_row(valid_row(unidad="", peso_min="5", peso_max="10"))


def test_rejects_missing_delivery_days():
    with pytest.raises(ValueError, match="entrega ausentes"):
        normalize_row(valid_row(dias_entrega=""))


def test_rejects_inverted_weight_range():
    with pytest.raises(ValueError, match="debe ser mayor"):
        normalize_row(valid_row(peso_min="5", peso_max="3", unidad="kg"))


def test_price_with_decimal_comma():
    price, _ = parse_price("1.391,04 MXN")
    assert price == Decimal("1391.04")


def test_rejects_negative_price():
    with pytest.raises(ValueError, match="mayor que cero"):
        parse_price("-703.95")


def test_rejects_unknown_carrier_and_zone_out_of_range():
    with pytest.raises(ValueError, match="desconocida"):
        parse_carrier("Paquetería Rayo")
    with pytest.raises(ValueError, match="permitido"):
        parse_zone("Zona 7")


def test_spanish_date_format():
    assert parse_date("1-ene-2026") == date(2026, 1, 1)


def test_importer_persists_batch_and_marks_normalized_duplicates(tmp_path):
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.db.base import Base
    from app.importers.tariffs import import_carriers, import_tariffs
    from app.models import ImportBatch, ImportRecord, Tariff

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    carriers_file = tmp_path / "paqueterias.csv"
    carriers_file.write_text(
        "carrier_id,nombre,tipo_servicio,activo\n"
        "CARR-01,DHL,aereo,si\n"
        "CARR-02,Estafeta,terrestre,si\n"
        "CARR-03,FedEx,aereo,si\n"
        "CARR-04,Redpack,terrestre,no\n",
        encoding="utf-8",
    )
    tariffs_file = tmp_path / "tarifas.csv"
    header = "paqueteria,zona,peso_min,peso_max,unidad,precio,dias_entrega,vigencia_desde\n"
    row = "DHL,Z1,0,1,kg,250.00,1,2026-01-01\n"
    tariffs_file.write_text(header + row + row, encoding="utf-8")

    with Session(engine) as session:
        import_carriers(session, carriers_file)
        report = import_tariffs(session, tariffs_file)
        session.commit()
        assert report == {"accepted": 0, "corrected": 1, "rejected": 1, "quarantined": 0}
        batch = session.scalar(select(ImportBatch))
        assert batch.total_rows == 2
        assert batch.rejected_rows == 1
        records = session.scalars(select(ImportRecord).order_by(ImportRecord.row_number)).all()
        assert [record.status for record in records] == ["corrected", "rejected"]
        assert session.scalar(select(Tariff.id)) is not None

    engine.dispose()


def test_normalize_row_reports_multiple_validation_errors():
    row = valid_row(
        unidad="",
        peso_min="5",
        peso_max="10",
        precio="-703.95",
        dias_entrega="",
        vigencia_desde="",
    )

    with pytest.raises(ValueError) as exc_info:
        normalize_row(row)

    message = str(exc_info.value)
    assert "Unidad de peso ausente" in message
    assert "precio" in message
    assert "entrega ausentes" in message
    assert "Fecha de vigencia ausente" in message


def create_tariff_test_session(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.base import Base
    from app.importers.tariffs import import_carriers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    carriers_file = tmp_path / "paqueterias.csv"
    carriers_file.write_text(
        "carrier_id,nombre,tipo_servicio,activo\n"
        "CARR-01,DHL,aereo,si\n",
        encoding="utf-8",
    )

    session = Session(engine)
    import_carriers(session, carriers_file)
    session.commit()

    return engine, session


def write_tariff_file(tmp_path, filename, row):
    header = (
        "paqueteria,zona,peso_min,peso_max,unidad,"
        "precio,dias_entrega,vigencia_desde\n"
    )
    path = tmp_path / filename
    path.write_text(header + row, encoding="utf-8")
    return path


def test_new_tariff_closes_previous_version(tmp_path):
    from sqlalchemy import select

    from app.importers.tariffs import import_tariffs
    from app.models import Tariff

    engine, session = create_tariff_test_session(tmp_path)

    try:
        old_file = write_tariff_file(
            tmp_path,
            "tarifa_anterior.csv",
            "DHL,Z3,0,1,kg,250.00,1,2026-01-01\n",
        )
        new_file = write_tariff_file(
            tmp_path,
            "tarifa_nueva.csv",
            "DHL,Z3,0,1,kg,300.00,1,2026-12-01\n",
        )

        import_tariffs(session, old_file)
        session.commit()

        report = import_tariffs(session, new_file)
        session.commit()

        tariffs = session.scalars(
            select(Tariff).order_by(Tariff.valid_from)
        ).all()

        assert report["accepted"] + report["corrected"] == 1
        assert len(tariffs) == 2
        assert tariffs[0].valid_to == date(2026, 11, 30)
        assert tariffs[1].valid_from == date(2026, 12, 1)
        assert tariffs[1].valid_to is None

    finally:
        session.close()
        engine.dispose()


def test_rejects_tariff_overlapping_future_version(tmp_path):
    from sqlalchemy import select

    from app.importers.tariffs import import_tariffs
    from app.models import Tariff

    engine, session = create_tariff_test_session(tmp_path)

    try:
        future_file = write_tariff_file(
            tmp_path,
            "tarifa_futura.csv",
            "DHL,Z3,0,1,kg,300.00,1,2026-12-01\n",
        )
        overlapping_file = write_tariff_file(
            tmp_path,
            "tarifa_intermedia.csv",
            "DHL,Z3,0,1,kg,275.00,1,2026-11-01\n",
        )

        import_tariffs(session, future_file)
        session.commit()

        report = import_tariffs(session, overlapping_file)
        session.commit()

        tariffs = session.scalars(select(Tariff)).all()

        assert report["rejected"] == 1
        assert len(tariffs) == 1
        assert tariffs[0].valid_from == date(2026, 12, 1)
        assert tariffs[0].valid_to is None

    finally:
        session.close()
        engine.dispose()


def test_rejects_tariff_already_imported_in_previous_batch(tmp_path):
    from sqlalchemy import select

    from app.importers.tariffs import import_tariffs
    from app.models import Tariff

    engine, session = create_tariff_test_session(tmp_path)

    try:
        tariff_file = write_tariff_file(
            tmp_path,
            "tarifa.csv",
            "DHL,Z3,0,1,kg,250.00,1,2026-01-01\n",
        )

        import_tariffs(session, tariff_file)
        session.commit()

        report = import_tariffs(session, tariff_file)
        session.commit()

        tariffs = session.scalars(select(Tariff)).all()

        assert report["rejected"] == 1
        assert len(tariffs) == 1
        assert tariffs[0].valid_to is None

    finally:
        session.close()
        engine.dispose()