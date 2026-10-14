"""Métricas objetivo para seleccionar modelos 1X2."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score, log_loss

UNIFORM_LOG_LOSS = float(np.log(3.0))


def combined_score(
    y_true: Any,
    probabilities: Any,
    predictions: Any | None = None,
    *,
    alpha: float = 1.0,
    beta: float = 1.0 / UNIFORM_LOG_LOSS,
) -> float:
    """Devuelve un score mayor-mejor: balanced accuracy menos log-loss normalizado."""
    probabilities_array = np.asarray(probabilities, dtype=float)
    y_array = np.asarray(y_true, dtype=int)
    if predictions is None:
        predictions_array = probabilities_array.argmax(axis=1)
    else:
        predictions_array = np.asarray(predictions, dtype=int)
    balanced = balanced_accuracy_score(y_array, predictions_array)
    loss = log_loss(y_array, probabilities_array, labels=[0, 1, 2])
    return float(alpha * balanced - beta * loss)


def score_breakdown(y_true: Any, predictions: Any, probabilities: Any) -> dict[str, float]:
    """Calcula las métricas y el score combinado en un diccionario serializable."""
    y_array = np.asarray(y_true, dtype=int)
    predictions_array = np.asarray(predictions, dtype=int)
    probabilities_array = np.asarray(probabilities, dtype=float)
    balanced = float(balanced_accuracy_score(y_array, predictions_array))
    loss = float(log_loss(y_array, probabilities_array, labels=[0, 1, 2]))
    return {
        "balanced_accuracy": balanced,
        "log_loss": loss,
        "combined_score": combined_score(y_array, probabilities_array, predictions_array),
    }
