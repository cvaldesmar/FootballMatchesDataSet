import csv
from types import SimpleNamespace

from src.football_dataset.context import ExecutionContext
from src.football_dataset.dataset_io import (
    HEADERS,
    SCHEMA_METADATA_PREFIX,
    append_season,
    iter_matches,
    save_all_seasons,
    write_csv_header,
)
from src.football_dataset.enrichment import migrate_csv_schema


def make_match(season, index):
    special_values = {
        "temporada": season,
        "rivalidad": 1,
        "campeonId": 7,
        "descensoConfirmadoLocal": 0,
        "descensoConfirmadoVisitante": 1,
        "presionLocal": 2,
        "presionVisitante": 3,
    }
    values = {header: special_values.get(header, str(index)) for header in HEADERS}
    return SimpleNamespace(**values)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as file:
        file.readline()
        return list(csv.DictReader(file, delimiter=";"))


def test_header_is_complete_and_stable(tmp_path):
    path = tmp_path / "dataset.csv"
    write_csv_header(path)

    with path.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        reader = csv.reader(file, delimiter=";")
        assert next(reader) == HEADERS


def test_append_season_serializes_new_variables_without_duplicate_header(tmp_path):
    path = tmp_path / "dataset.csv"
    season = SimpleNamespace(jornadas={1: {1: make_match("2021-22", 1)}})
    write_csv_header(path)

    assert append_season(path, season) == 1
    assert append_season(path, season) == 1
    rows = read_rows(path)

    assert len(rows) == 2
    assert rows[0]["temporada"] == "2021-22"
    assert rows[0]["campeonId"] == "7"
    assert rows[0]["descensoConfirmadoVisitante"] == "1"
    assert rows[0]["presionLocal"] == "2"
    assert rows[0]["rivalidad"] == "1"


def test_save_all_seasons_concatenates_seasons_without_mixing_rows(tmp_path):
    first = make_match("2020-21", 1)
    second = make_match("2021-22", 2)
    context = ExecutionContext(output_path=str(tmp_path / "all.csv"))
    context.add_season(1, "2020-21", SimpleNamespace(jornadas={1: {1: first}}))
    context.add_season(1, "2021-22", SimpleNamespace(jornadas={1: {2: second}}))

    assert save_all_seasons(context) == 2
    rows = read_rows(tmp_path / "all.csv")
    assert [row["temporada"] for row in rows] == ["2020-21", "2021-22"]
    assert [row["idPartido"] for row in rows] == ["1", "2"]


def test_iter_matches_yields_all_registered_matches(tmp_path):
    context = ExecutionContext()
    first = make_match("2020-21", 1)
    second = make_match("2021-22", 2)
    context.add_season(1, "2020-21", SimpleNamespace(jornadas={1: {1: first}}))
    context.add_season(2, "2021-22", SimpleNamespace(jornadas={1: {2: second}}))

    assert list(iter_matches(context)) == [first, second]


def test_migrate_csv_schema_adds_distance_and_preserves_enrichment(tmp_path):
    source = tmp_path / "legacy.csv"
    destination = tmp_path / "migrated.csv"
    legacy_headers = [header for header in HEADERS if header != "distanciaKm"]
    row = {header: str(index) for index, header in enumerate(legacy_headers)}
    row.update(
        {
            "localName": "Real Madrid",
            "visitanteName": "Atlético de Madrid",
            "localMarketValue": "123.5",
            "visitanteMarketValue": "98.25",
            "arbitroName": "Árbitro Test",
            "arbitroId": "42",
        }
    )
    with source.open("w", encoding="utf-8", newline="") as file:
        file.write("# football_dataset_schema=1\n")
        writer = csv.DictWriter(file, fieldnames=legacy_headers, delimiter=";")
        writer.writeheader()
        writer.writerow(row)

    assert migrate_csv_schema(source, destination) == 1

    with destination.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        reader = csv.DictReader(file, delimiter=";")
        migrated = next(reader)
    assert reader.fieldnames == HEADERS
    assert float(migrated["distanciaKm"]) > 0
    assert migrated["localMarketValue"] == "123.5"
    assert migrated["visitanteMarketValue"] == "98.25"
    assert migrated["arbitroName"] == "Árbitro Test"
    assert migrated["arbitroId"] == "42"


def test_migrate_csv_schema_accepts_legacy_csv_without_metadata(tmp_path):
    source = tmp_path / "legacy-without-metadata.csv"
    headers = [header for header in HEADERS if header != "distanciaKm"]
    row = {header: "" for header in headers}
    row.update({"localName": "Barcelona", "visitanteName": "Real Madrid"})
    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers, delimiter=";")
        writer.writeheader()
        writer.writerow(row)

    assert migrate_csv_schema(source) == 1
    with source.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        reader = csv.DictReader(file, delimiter=";")
        migrated = next(reader)
    assert reader.fieldnames == HEADERS
    assert float(migrated["distanciaKm"]) > 0
