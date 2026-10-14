from datetime import date

import pandas as pd
import pytest

from src.football_dataset.ml_features import ML_COLUMNS, ML_METADATA_PREFIX
from src.football_ml.fixtures import cutoff_history, load_fixtures
from src.football_ml.io import load_ml_dataset
from src.football_ml.predict import predict_frame
from src.football_ml.selection import filter_by_min_season, filter_last_seasons
from src.football_ml.snapshots import build_fixture_features
from src.football_ml.split import temporal_split
from src.football_ml.train import train_model


def make_frame(
    seasons: tuple[str, ...] = ("1990-91", "2018-19", "2019-20", "2020-21", "2021-22"),
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for season_index, season in enumerate(seasons):
        for match_index in range(4):
            row = {column: 0 for column in ML_COLUMNS}
            row.update(
                {
                    "division": 1,
                    "temporada": season,
                    "jornada": match_index + 1,
                    "localId": match_index + 1,
                    "visitanteId": match_index + 10,
                    "diferenciaPuntos": 3 if match_index % 2 == 0 else -3,
                    "diferenciaPosicion": 1,
                    "diferenciaGolesNeta": 2,
                    "rachaLocal": 1,
                    "rachaVisitante": 0,
                    "h2hMatches": 1,
                    "h2hBalance": 1,
                    "campeonDecidido": 0,
                    "descensoConfirmadoLocal": 0,
                    "descensoConfirmadoVisitante": 0,
                    "presionLocal": 1,
                    "presionVisitante": 1,
                    "rivalidad": 0,
                    "distanciaKm": -1,
                    "diferenciaValorMercado": -1,
                    "ratioValorMercado": -1,
                    "resultado1X2": ("1", "X", "2")[(season_index + match_index) % 3],
                }
            )
            rows.append(row)
    return pd.DataFrame(rows, columns=ML_COLUMNS)


def test_selection_discards_old_seasons_before_pipeline():
    frame, report = filter_by_min_season(make_frame(), "2019-20")

    assert report.discarded_rows == 8
    assert set(frame["temporada"]) == {"2019-20", "2020-21", "2021-22"}
    assert report.min_year == 2019


def test_last_seasons_keeps_only_recent_distinct_seasons():
    frame, report = filter_last_seasons(make_frame(), 2)

    assert report.seasons == ("2020-21", "2021-22")
    assert len(frame) == 8


def test_temporal_split_has_disjoint_ordered_seasons():
    split = temporal_split(
        make_frame()[make_frame()["temporada"] != "1990-91"], test_seasons=1, validation_seasons=1
    )

    assert split.train_seasons == ("2018-19", "2019-20")
    assert split.validation_seasons == ("2020-21",)
    assert split.test_seasons == ("2021-22",)
    assert not set(split.train_seasons) & set(split.test_seasons)


def test_training_persists_artifact_and_predicts(tmp_path):
    artifact_path = tmp_path / "model.joblib"
    artifact = train_model(
        make_frame()[make_frame()["temporada"] != "1990-91"],
        artifact_path,
        min_season="2018-19",
        test_seasons=1,
        validation_seasons=1,
    )

    assert artifact_path.exists()
    assert artifact["selection"]["discarded_rows"] == 0
    result = predict_frame(artifact, make_frame().tail(1))
    assert list(result.columns) == [
        "prediccion",
        "probabilidad_1",
        "probabilidad_X",
        "probabilidad_2",
    ]
    assert result.iloc[0]["prediccion"] in {"1", "X", "2"}
    assert result.iloc[0][
        ["probabilidad_1", "probabilidad_X", "probabilidad_2"]
    ].sum() == pytest.approx(1.0)


def test_load_ml_dataset_validates_metadata(tmp_path):
    path = tmp_path / "dataset.csv"
    path.write_text("# wrong\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Metadato incompatible"):
        load_ml_dataset(path)


def test_load_ml_dataset_reads_valid_file(tmp_path):
    path = tmp_path / "dataset.csv"
    row = make_frame().iloc[0].to_dict()
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(ML_METADATA_PREFIX + "\n")
        file.write(";".join(ML_COLUMNS) + "\n")
        file.write(";".join(str(row[column]) for column in ML_COLUMNS) + "\n")

    loaded = load_ml_dataset(path)
    assert len(loaded) == 1
    assert loaded.iloc[0]["resultado1X2"] in {"1", "X", "2"}


def historical_row(match_date: str, home_goals: int, away_goals: int) -> dict[str, object]:
    return {
        "division": 1,
        "temporada": "2025-26",
        "jornada": 1,
        "matchDate": match_date,
        "localId": 1,
        "visitanteId": 2,
        "golesLocal": home_goals,
        "golesVisitante": away_goals,
    }


def test_fixtures_reject_results_and_cutoff_is_inclusive(tmp_path):
    frame = pd.DataFrame(
        [
            {
                "division": 1,
                "temporada": "2026-27",
                "jornada": 2,
                "matchDate": "2026-10-20",
                "localId": 1,
                "visitanteId": 2,
            }
        ]
    )
    history = pd.DataFrame(
        [
            historical_row("2026-10-14", 1, 0),
            historical_row("2026-10-15", 0, 1),
        ]
    )
    assert len(cutoff_history(history, date(2026, 10, 14))) == 1

    invalid_path = tmp_path / "fixtures-invalid.csv"
    frame.assign(resultado1X2="1").to_csv(invalid_path, sep=";", index=False)
    with pytest.raises(ValueError, match="no pueden incluir resultados"):
        load_fixtures(invalid_path)


def test_future_matches_cannot_change_snapshot_features():
    fixture = pd.DataFrame(
        [
            {
                "division": 1,
                "temporada": "2025-26",
                "jornada": 2,
                "matchDate": date(2025, 9, 8),
                "localId": 1,
                "visitanteId": 2,
            }
        ]
    )
    before = pd.DataFrame(
        [
            historical_row("2025-09-01", 1, 0),
            historical_row("2025-09-20", 0, 5),
        ]
    )
    after = before.copy()
    after.loc[1, "golesLocal"] = 99
    first = build_fixture_features(before, fixture, date(2025, 9, 10))
    second = build_fixture_features(after, fixture, date(2025, 9, 10))
    pd.testing.assert_frame_equal(first, second)
