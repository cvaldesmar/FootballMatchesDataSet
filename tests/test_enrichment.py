import csv
import json
from pathlib import Path

from src.football_dataset.dataset_io import HEADERS, SCHEMA_METADATA_PREFIX
from src.football_dataset.enrichment import enrich_csv, migrate_dataset_csv


def write_dataset(path: Path) -> dict[str, str]:
    row = {header: "" for header in HEADERS}
    row.update(
        {
            "idPartido": "1",
            "division": "1",
            "temporada": "2021-22",
            "jornada": "1",
            "matchDate": "2021-09-12",
            "localName": "Barcelona",
            "visitanteName": "Real Madrid",
            "localMarketValue": "-1",
            "visitanteMarketValue": "-1",
            "arbitroName": "",
            "arbitroId": "-1",
        }
    )
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(SCHEMA_METADATA_PREFIX + "\n")
        writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerow(row)
    return row


def write_cache(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_enrich_csv_uses_only_persisted_caches(tmp_path):
    source = tmp_path / "historico.csv"
    destination = tmp_path / "enriquecido.csv"
    market = tmp_path / "market.json"
    referees = tmp_path / "referees.json"
    write_dataset(source)
    write_cache(
        market,
        {
            "version": 3,
            "cache": {
                "FC Barcelona": {"2021-08-01": 500.0},
                "Real Madrid CF": {"2021-08-01": 700.0},
            },
        },
    )
    write_cache(
        referees,
        {
            "version": 2,
            "cache": {"2021": {"1": {"2021-09-12-Barcelona-Real Madrid": ["Ref Test", 42, "2:1"]}}},
        },
    )

    assert enrich_csv(source, destination, market, referees) == 1
    with destination.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        rows = list(csv.DictReader(file, delimiter=";"))

    assert list(rows[0]) == HEADERS
    assert rows[0]["localMarketValue"] == "500.0"
    assert rows[0]["visitanteMarketValue"] == "700.0"
    assert rows[0]["arbitroName"] == "Ref Test"
    assert rows[0]["arbitroId"] == "42"


def test_migrate_dataset_csv_from_schema_v1_is_atomic_and_preserves_enrichment(tmp_path):
    source = tmp_path / "legacy.csv"
    destination = tmp_path / "migrated.csv"
    legacy_headers = [header for header in HEADERS if header != "distanciaKm"]
    row = {header: "" for header in legacy_headers}
    row.update(
        {
            "idPartido": "7",
            "localName": "Barcelona",
            "visitanteName": "Real Madrid",
            "localMarketValue": "123.0",
            "visitanteMarketValue": "456.0",
            "arbitroName": "Árbitro Persistido",
            "arbitroId": "99",
        }
    )
    with source.open("w", encoding="utf-8", newline="") as file:
        file.write("# football_dataset_schema=1\n")
        writer = csv.DictWriter(file, fieldnames=legacy_headers, delimiter=";")
        writer.writeheader()
        writer.writerow(row)

    assert migrate_dataset_csv(source, destination) == 1
    with destination.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        reader = csv.DictReader(file, delimiter=";")
        migrated = next(reader)

    assert reader.fieldnames == HEADERS
    assert float(migrated["distanciaKm"]) > 0
    assert migrated["localMarketValue"] == "123.0"
    assert migrated["visitanteMarketValue"] == "456.0"
    assert migrated["arbitroName"] == "Árbitro Persistido"
    assert migrated["arbitroId"] == "99"


def test_migrate_dataset_csv_updates_in_place_and_accepts_schema_v2(tmp_path):
    source = tmp_path / "dataset.csv"
    write_dataset(source)

    assert migrate_dataset_csv(source) == 1
    with source.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        rows = list(csv.DictReader(file, delimiter=";"))

    assert list(rows[0]) == HEADERS
    assert float(rows[0]["distanciaKm"]) > 0
