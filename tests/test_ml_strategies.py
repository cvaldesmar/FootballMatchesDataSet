import numpy as np
import pandas as pd

from src.football_ml.poisson import Poisson1X2Classifier
from src.football_ml.staged import Staged1X2Classifier


def strategy_frame() -> pd.DataFrame:
    rows = []
    for index in range(18):
        rows.append(
            {
                "division": 1,
                "temporada": "2020-21",
                "jornada": index // 3 + 1,
                "localId": index % 3 + 1,
                "visitanteId": index % 3 + 10,
                "diferenciaPuntos": index % 5 - 2,
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
                "resultado1X2": ("1", "X", "2")[index % 3],
            }
        )
    return pd.DataFrame(rows)


def test_staged_classifier_probabilities_are_coherent():
    frame = strategy_frame()
    model = Staged1X2Classifier(C=1.0)
    model.fit(frame, frame["resultado1X2"].map({"1": 0, "X": 1, "2": 2}))

    probabilities = model.predict_proba(frame.head(5))

    assert probabilities.shape == (5, 3)
    assert np.all(probabilities >= 0)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)
    assert set(model.predict(frame.head(5))).issubset({0, 1, 2})


def test_poisson_classifier_derives_coherent_1x2_probabilities():
    frame = strategy_frame()
    model = Poisson1X2Classifier(alpha=0.5, max_goals=8)
    model.fit_goals(
        frame,
        np.where(frame["resultado1X2"] == "1", 2, 0),
        np.where(frame["resultado1X2"] == "2", 2, 0),
    )

    probabilities = model.predict_proba(frame.head(5))

    assert probabilities.shape == (5, 3)
    assert np.all(probabilities >= 0)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)
    assert set(model.predict(frame.head(5))).issubset({0, 1, 2})
