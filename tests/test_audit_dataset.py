import csv
from pathlib import Path

import pytest

from src.football_dataset.audit import audit_dataset


def write_audit_csv(path, rows, columns=None):
    columns = columns or [
        "division",
        "temporada",
        "jornada",
        "idPartido",
        "resultado1X2",
        "distanciaKm",
        "golesLocal",
        "golesVisitante",
        "golDiff",
        "puntosLocal",
        "puntosVisitante",
        "golesafavorlocal",
        "golesencontralocal",
        "golesafavorvisitante",
        "golesencontravisitante",
        "rachaLocal",
        "rachaVisitante",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write("# football_dataset_ml=1\n")
        writer = csv.DictWriter(file, fieldnames=columns, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def test_audit_detects_duplicate_and_invalid_target(tmp_path):
    path = tmp_path / "dataset.csv"
    row = {
        column: "0"
        for column in [
            "division",
            "temporada",
            "jornada",
            "idPartido",
            "resultado1X2",
            "distanciaKm",
        ]
    }
    row.update(
        {
            "division": "1",
            "temporada": "2021-22",
            "jornada": "1",
            "idPartido": "1",
            "resultado1X2": "1",
            "distanciaKm": "10",
        }
    )
    write_audit_csv(path, [row, row | {"resultado1X2": "bad"}], list(row))

    report = audit_dataset(path)

    assert not report["ok"]
    assert report["duplicate_rows"] == 1
    assert any("resultado1X2" in issue for issue in report["issues"])


def test_audit_reports_round_gaps_and_valid_target_counts(tmp_path):
    path = tmp_path / "dataset.csv"
    base = {
        column: "0"
        for column in [
            "division",
            "temporada",
            "jornada",
            "idPartido",
            "resultado1X2",
            "distanciaKm",
        ]
    }
    base.update({"division": "1", "temporada": "2021-22", "resultado1X2": "X", "distanciaKm": "-1"})
    write_audit_csv(
        path,
        [
            base | {"jornada": "1", "idPartido": "1", "resultado1X2": "1"},
            base | {"jornada": "3", "idPartido": "2"},
        ],
        list(base),
    )

    report = audit_dataset(path)

    assert report["ok"]
    assert report["target_counts"] == {"1": 1, "X": 1}
    assert report["seasons"]["division=1;temporada=2021-22"]["gaps"] == [2]
    assert any("Jornadas ausentes" in warning for warning in report["warnings"])


def test_audit_detects_score_and_inter_round_accumulation_errors(tmp_path):
    path = tmp_path / "dataset.csv"
    base = {
        column: "0"
        for column in [
            "division",
            "temporada",
            "jornada",
            "idPartido",
            "localId",
            "visitanteId",
            "resultado1X2",
            "distanciaKm",
            "golesLocal",
            "golesVisitante",
            "golDiff",
            "puntosLocal",
            "puntosVisitante",
            "golesafavorlocal",
            "golesencontralocal",
            "golesafavorvisitante",
            "golesencontravisitante",
            "rachaLocal",
            "rachaVisitante",
        ]
    }
    base.update(
        {
            "division": "1",
            "temporada": "2021-22",
            "resultado1X2": "1",
            "golesLocal": "2",
            "golesVisitante": "0",
            "golDiff": "9",
        }
    )
    write_audit_csv(
        path,
        [
            base | {"jornada": "1", "idPartido": "1", "localId": "10", "puntosLocal": "1"},
            base | {"jornada": "2", "idPartido": "2", "localId": "10", "puntosLocal": "0"},
        ],
        list(base),
    )

    report = audit_dataset(path)

    assert not report["ok"]
    assert any("diferencias de goles incoherentes" in issue for issue in report["issues"])
    assert any("empiezan a cero" in issue for issue in report["issues"])
    assert any("disminuyen entre jornadas" in issue for issue in report["issues"])


def test_ml_audit_uses_team_identity_for_duplicate_detection(tmp_path):
    path = tmp_path / "dataset_ml.csv"
    columns = [
        "division",
        "temporada",
        "jornada",
        "localId",
        "visitanteId",
        "resultado1X2",
    ]
    row = {
        "division": "1",
        "temporada": "2021-22",
        "jornada": "1",
        "localId": "10",
        "visitanteId": "20",
        "resultado1X2": "X",
    }
    write_audit_csv(path, [row, row], columns)

    report = audit_dataset(path)

    assert report["duplicate_rows"] == 1
    assert not report["ok"]


@pytest.mark.parametrize(
    "dataset_name",
    [
        "dataset_historico_1970_2025.csv",
        "dataset_historico_1970_2025_enriquecido.csv",
        "dataset_ml.csv",
    ],
)
def test_real_datasets_pass_offline_audit(dataset_name):
    report = audit_dataset(Path("data") / dataset_name)

    assert report["ok"], report["issues"]
    assert report["rows"] == 43884
    assert report["target_counts"] == {"1": 21794, "X": 12165, "2": 9925}
