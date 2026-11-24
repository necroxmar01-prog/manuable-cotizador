import argparse
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.importers.tariffs import import_carriers, import_tariffs
from app.models import ImportBatch

DATA_DIR = Path("/app/datos")


def seed_if_empty() -> None:
    with SessionLocal.begin() as session:
        existing_batch = session.scalar(select(ImportBatch.id).limit(1))
        if existing_batch:
            print("Los datos iniciales ya fueron procesados; se omite la carga automática.")
            return
        import_carriers(session, DATA_DIR / "paqueterias.csv")
        report = import_tariffs(session, DATA_DIR / "tarifas.csv")
        print("Importación inicial de tarifas:")
        print(f"  Aceptadas: {report['accepted']}")
        print(f"  Corregidas: {report['corrected']}")
        print(f"  Rechazadas: {report['rejected']}")


def import_file(path: Path) -> None:
    with SessionLocal.begin() as session:
        report = import_tariffs(session, path)
    print(f"Resultado de {path.name}: {report}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comandos de datos de Manuable")
    parser.add_argument("command", choices=["seed-if-empty", "import-tariffs"])
    parser.add_argument("file", nargs="?", type=Path)
    args = parser.parse_args()
    if args.command == "seed-if-empty":
        seed_if_empty()
    else:
        if not args.file:
            parser.error("import-tariffs requiere la ruta del CSV")
        import_file(args.file)
