"""Modelos de referencia simples para medir el valor del pipeline."""

from __future__ import annotations

import pandas as pd

from .preprocessing import target_series


def majority_prediction(train: pd.DataFrame, frame: pd.DataFrame) -> pd.Series:
    """Predice siempre la clase más frecuente observada en train."""
    target = target_series(train)
    majority = int(target.mode().iloc[0])
    return pd.Series(majority, index=frame.index, dtype="int64")


def home_advantage_prediction(frame: pd.DataFrame) -> pd.Series:
    """Heurística interpretable basada en la diferencia de puntos prepartido."""
    points = pd.to_numeric(frame["diferenciaPuntos"], errors="coerce").fillna(0)
    # La igualdad se considera empate; una ventaja negativa favorece al visitante.
    return points.apply(lambda value: 0 if value > 0 else (1 if value == 0 else 2)).astype("int64")
