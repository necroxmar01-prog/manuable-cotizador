import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.importers.historical_quotes import import_historical_quotes
from app.importers.pricing_rules import import_pricing_rules
from app.importers.sync import sync_data
from app.importers.tariffs import import_tariffs

DATA_DIR = Path("/app/datos")


def run_sync(data_dir: Path) -> None:
    with SessionLocal.begin() as session:
        for line in sync_data(session, data_dir):
            print(line)


def run_import(importer, path: Path) -> None:
    with SessionLocal.begin() as session:
        report = importer(session, path)
    print(f"Resultado de {path.name}: {report}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comandos de datos de Manuable")
    parser.add_argument(
        "command",
        choices=[
            "sync-data",
            "seed-if-empty",  # alias de fase 1
            "import-tariffs",
            "import-pricing-rules",
            "import-historical-quotes",
        ],
    )
    parser.add_argument("file", nargs="?", type=Path)
    args = parser.parse_args()

    if args.command in {"sync-data", "seed-if-empty"}:
        run_sync(args.file or DATA_DIR)
    else:
        if not args.file:
            parser.error(f"{args.command} requiere la ruta del CSV")
        importer = {
            "import-tariffs": import_tariffs,
            "import-pricing-rules": import_pricing_rules,
            "import-historical-quotes": import_historical_quotes,
        }[args.command]
        run_import(importer, args.file)
