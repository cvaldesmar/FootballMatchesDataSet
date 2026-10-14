"""Modelo de goles Poisson y derivación de probabilidades 1X2."""

from __future__ import annotations

from math import factorial
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import PoissonRegressor

from .preprocessing import add_missing_indicators, build_preprocessor


class Poisson1X2Classifier(BaseEstimator, ClassifierMixin):
    """Predice goles de ambos equipos y deriva probabilidades de resultado."""

    def __init__(self, *, alpha: float = 1.0, max_goals: int = 10) -> None:
        self.alpha = alpha
        self.max_goals = max_goals

    def fit(self, X: pd.DataFrame, y: Any) -> Poisson1X2Classifier:
        raise ValueError(
            "Poisson1X2Classifier necesita fit_goals(X, home_goals, away_goals); "
            "no puede entrenarse con solo la etiqueta 1X2"
        )

    def fit_goals(self, X: pd.DataFrame, home_goals: Any, away_goals: Any) -> Poisson1X2Classifier:
        prepared = add_missing_indicators(X)
        self.preprocessor_ = build_preprocessor(X)
        transformed = self.preprocessor_.fit_transform(prepared)
        self.home_model_ = PoissonRegressor(alpha=self.alpha, max_iter=500)
        self.away_model_ = PoissonRegressor(alpha=self.alpha, max_iter=500)
        self.home_model_.fit(transformed, np.asarray(home_goals, dtype=float))
        self.away_model_.fit(transformed, np.asarray(away_goals, dtype=float))
        self.classes_ = np.array([0, 1, 2])
        return self

    def _goal_probabilities(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        transformed = self.preprocessor_.transform(add_missing_indicators(X))
        home_lambda = np.maximum(self.home_model_.predict(transformed), 1e-6)
        away_lambda = np.maximum(self.away_model_.predict(transformed), 1e-6)
        values = np.arange(self.max_goals + 1)
        factorials = np.array([factorial(int(x)) for x in values], dtype=float)
        home = np.array([np.exp(-rate) * rate**values / factorials for rate in home_lambda])
        away = np.array([np.exp(-rate) * rate**values / factorials for rate in away_lambda])
        return home, away

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        home, away = self._goal_probabilities(X)
        result = np.zeros((len(X), 3), dtype=float)
        for home_goals in range(self.max_goals + 1):
            for away_goals in range(self.max_goals + 1):
                probability = home[:, home_goals] * away[:, away_goals]
                result[
                    :, 0 if home_goals > away_goals else 1 if home_goals == away_goals else 2
                ] += probability
        return result / result.sum(axis=1, keepdims=True)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1).astype(int)
