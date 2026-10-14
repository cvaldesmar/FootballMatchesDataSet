import numpy as np
import pandas as pd

from src.football_ml.score import combined_score, score_breakdown
from src.football_ml.walk_forward import ordered_rounds, walk_forward_evaluate


def optimization_frame() -> pd.DataFrame:
    rows = []
    for season_index, season in enumerate(("2021-22", "2022-23")):
        for jornada in range(1, 7):
            for match in range(3):
                result = ("1", "X", "2")[(season_index + jornada + match) % 3]
                rows.append(
                    {
                        "division": 1,
                        "temporada": season,
                        "jornada": jornada,
                        "localId": match + 1,
                        "visitanteId": match + 10,
                        "diferenciaPuntos": jornada - 3,
                        "diferenciaPosicion": 0,
                        "diferenciaGolesNeta": 0,
                        "rachaLocal": 0,
                        "rachaVisitante": 0,
                        "h2hMatches": 0,
                        "h2hBalance": 0,
                        "campeonDecidido": 0,
                        "descensoConfirmadoLocal": 0,
                        "descensoConfirmadoVisitante": 0,
                        "presionLocal": 0,
                        "presionVisitante": 0,
                        "rivalidad": 0,
                        "distanciaKm": -1,
                        "diferenciaValorMercado": -1,
                        "ratioValorMercado": -1,
                        "resultado1X2": result,
                    }
                )
    return pd.DataFrame(rows)


def test_combined_score_rewards_balanced_accuracy_and_good_probabilities():
    y_true = np.array([0, 1, 2, 0, 1, 2])
    good = np.eye(3)[y_true] * 0.7 + 0.1
    bad = np.full((6, 3), 1 / 3)

    assert combined_score(y_true, good) > combined_score(y_true, bad)
    breakdown = score_breakdown(y_true, y_true, good)
    assert set(breakdown) == {"balanced_accuracy", "log_loss", "combined_score"}


def test_walk_forward_uses_only_previous_rounds():
    frame = optimization_frame()
    rounds = ordered_rounds(frame)
    observed = []

    class RecordingModel:
        def fit(self, train, target):
            observed.append((train["temporada"].iloc[-1], train["jornada"].max()))
            self.classes_ = np.array([0, 1, 2])
            return self

        def predict(self, valid):
            return np.zeros(len(valid), dtype=int)

        def predict_proba(self, valid):
            return np.tile([[0.6, 0.2, 0.2]], (len(valid), 1))

    result = walk_forward_evaluate(
        frame,
        lambda train, params: RecordingModel(),
        min_train_rounds=2,
        max_validation_rounds=3,
    )

    assert result.rows_evaluated == 9
    assert len(observed) == 3
    assert observed[0][1] == 2
    assert result.rounds[0]["jornada"] == 3
    assert rounds[2] == ("2021-22", 3)


def test_tune_smoke_persists_champion(tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("optuna")
    from src.football_ml.tuning import tune_catalog

    artifact_path = tmp_path / "champion.joblib"
    artifact = tune_catalog(
        optimization_frame(),
        ("logistic",),
        n_trials=1,
        min_train_rounds=2,
        max_validation_rounds=1,
        output_path=artifact_path,
    )

    assert artifact_path.exists()
    assert artifact["model_name"] == "logistic"
    assert "combined_score" in artifact["walk_forward_metrics"]
    assert artifact["catalog_results"][0]["params"]
