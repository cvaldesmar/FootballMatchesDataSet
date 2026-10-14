"""Clasificador jerárquico: empate/no empate y ganador local/visitante."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression

from .models import RANDOM_STATE
from .preprocessing import add_missing_indicators, build_preprocessor, target_series


class Staged1X2Classifier(BaseEstimator, ClassifierMixin):
    """Combina dos clasificadores binarios en probabilidades 1/X/2 coherentes."""

    def __init__(self, *, C: float = 1.0, class_weight: str | None = "balanced") -> None:
        self.C = C
        self.class_weight = class_weight

    def fit(self, X: pd.DataFrame, y: Any) -> Staged1X2Classifier:
        target = np.asarray(y, dtype=int)
        if not set(target).issubset({0, 1, 2}):
            raise ValueError("El target debe usar 0=1, 1=X, 2=2")
        self.preprocessor_ = build_preprocessor(X)
        transformed = self.preprocessor_.fit_transform(add_missing_indicators(X))
        self.draw_model_ = LogisticRegression(
            C=self.C,
            class_weight=self.class_weight,
            max_iter=1000,
            random_state=RANDOM_STATE,
        )
        self.draw_model_.fit(transformed, (target == 1).astype(int))
        non_draw = target != 1
        self.winner_model_ = LogisticRegression(
            C=self.C,
            class_weight=self.class_weight,
            max_iter=1000,
            random_state=RANDOM_STATE,
        )
        self.winner_model_.fit(transformed[non_draw], (target[non_draw] == 0).astype(int))
        self.classes_ = np.array([0, 1, 2])
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        transformed = self.preprocessor_.transform(add_missing_indicators(X))
        draw_probability = self.draw_model_.predict_proba(transformed)[:, 1]
        winner_probability = self.winner_model_.predict_proba(transformed)[:, 1]
        result = np.column_stack(
            [
                (1.0 - draw_probability) * winner_probability,
                draw_probability,
                (1.0 - draw_probability) * (1.0 - winner_probability),
            ]
        )
        return result / result.sum(axis=1, keepdims=True)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1).astype(int)


def staged_target(frame: pd.DataFrame) -> pd.Series:
    """Codifica el target usando el mismo contrato que el resto del pipeline."""
    return target_series(frame)
