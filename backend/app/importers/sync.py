"""Sincroniza la carpeta ``datos/`` con la base de datos al arrancar.

Cada archivo se importa una sola vez por contenido (SHA-256). Para el próximo
cambio de tarifas basta con dejar un CSV nuevo (``tarifas_<algo>.csv``,
``reglas_peso*.csv``) en ``datos/`` y reiniciar el backend, o correr
``python -m app.cli sync-data``. No hay que tocar código.
"""

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.historical_quotes import import_historical_quotes
from app.importers.pricing_rules import import_pricing_rules
from app.importers.tariffs import (
    file_sha256,
    import_carriers,
    import_tariffs,
    quarantine_price_outliers,
)
from app.models import ImportBatch

# (patrón de archivo, importador). El orden importa: las reglas y las
# cotizaciones históricas se validan contra paqueterías y tarifas ya cargadas.
SOURCES: list[tuple[str, Callable[[Session, Path], dict[str, int]]]] = [
    ("tarifas*.csv", import_tariffs),
    ("reglas_peso*.csv", import_pricing_rules),
    ("cotizaciones_historicas*.csv", import_historical_quotes),
]


def already_imported(session: Session, path: Path, digest: str, legacy_ok: bool) -> bool:
    if session.scalar(select(ImportBatch.id).where(ImportBatch.file_sha256 == digest).limit(1)):
        return True
    if not legacy_ok:
        return False
    # Fase 1 solo cargó tarifas.csv y no guardaba hash: se identifica por
    # nombre y se le asigna el hash actual para comparar por contenido después.
    legacy = session.scalar(
        select(ImportBatch).where(
            ImportBatch.source_file == path.name,
            ImportBatch.kind == "tariffs",
            ImportBatch.file_sha256.is_(None),
        ).limit(1)
    )
    if legacy is not None:
        legacy.file_sha256 = digest
        return True
    return False


def sync_data(session: Session, data_dir: Path) -> list[str]:
    log: list[str] = []
    carriers_file = data_dir / "paqueterias.csv"
    if carriers_file.exists():
        created = import_carriers(session, carriers_file)
        log.append(f"paqueterias.csv: catálogo actualizado ({created} nuevas)")

    for pattern, importer in SOURCES:
        for path in sorted(data_dir.glob(pattern)):
            digest = file_sha256(path)
            if already_imported(session, path, digest, legacy_ok=importer is import_tariffs):
                log.append(f"{path.name}: sin cambios, se omite")
                continue
            report = importer(session, path)
            session.flush()
            log.append(f"{path.name}: {report}")

    quarantined = quarantine_price_outliers(session)
    if quarantined:
        log.append(f"Tarifas en cuarentena por precio atípico: {len(quarantined)}")
    return log
