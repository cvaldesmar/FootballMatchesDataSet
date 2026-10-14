import csv
from pathlib import Path

from src.football_dataset.dataset_io import HEADERS, SCHEMA_METADATA_PREFIX
from src.football_dataset.ml_features import ML_COLUMNS, build_ml_features, transform_rows


def source_row():
    row = {column: "0" for column in HEADERS}
    row.update(
        {
            "division": "1",
            "temporada": "2021-22",
            "jornada": "2",
            "localMarketValue": "200",
            "visitanteMarketValue": "100",
            "puntosLocal": "4",
            "puntosVisitante": "1",
            "posicionLocal": "2",
            "posicionVisitante": "8",
            "golesafavorlocal": "5",
            "golesencontralocal": "2",
            "golesafavorvisitante": "2",
            "golesencontravisitante": "5",
            "resultado1X2": "1",
        }
    )
    return row


def write_source(path: Path, row):
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(SCHEMA_METADATA_PREFIX + "\n")
        writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerow(row)


def test_transform_rows_creates_expected_synthetic_features():
    result = transform_rows([source_row()])[0]

    assert result["diferenciaGolesNeta"] == "6.0"
    assert result["diferenciaValorMercado"] == "100.0"
    assert result["ratioValorMercado"] == "2.0"
    assert result["diferenciaPosicion"] == "6.0"
    assert result["h2hBalance"] == "0.0"
    assert result["campeonDecidido"] == "1"
    assert list(result) == ML_COLUMNS


def test_transform_rows_is_independent_of_input_order():
    first, second = source_row(), dict(source_row(), idPartido="2")
    assert transform_rows([first, second]) == transform_rows([second, first])[::-1]


def test_build_ml_features_preserves_source_and_uses_separate_output(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "ml.csv"
    write_source(source, source_row())
    original = source.read_bytes()

    assert build_ml_features(source, output) == 1
    assert source.read_bytes() == original
    with output.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == "# football_dataset_ml=1"
        rows = list(csv.DictReader(file, delimiter=";"))
    assert list(rows[0]) == ML_COLUMNS
    assert rows[0]["resultado1X2"] == "1"


def test_advanced_features_use_only_previous_jornadas():
    first = {column: "0" for column in HEADERS}
    first.update(
        {
            "division": "1",
            "temporada": "2021-22",
            "jornada": "1",
            "matchDate": "2021-08-01",
            "localId": "1",
            "visitanteId": "2",
            "golesLocal": "2",
            "golesVisitante": "0",
            "localMarketValue": "100",
            "visitanteMarketValue": "50",
            "resultado1X2": "1",
        }
    )
    second = dict(first)
    second.update(
        {
            "jornada": "2",
            "matchDate": "2021-08-08",
            "golesLocal": "0",
            "golesVisitante": "0",
            "resultado1X2": "X",
        }
    )

    transformed = transform_rows([first, second])

    assert transformed[0]["golesFavor5Local"] == "0.0"
    assert transformed[0]["diasDescansoLocal"] == "-1.0"
    assert transformed[1]["golesFavor5Local"] == "2.0"
    assert transformed[1]["golesContra5Local"] == "0.0"
    assert transformed[1]["rachaLocalCasa"] == "1.0"
    assert transformed[1]["partidosCasaLocal"] == "1"
    assert transformed[1]["diasDescansoLocal"] == "7.0"
    assert transformed[1]["partidos7DiasLocal"] == "1"
