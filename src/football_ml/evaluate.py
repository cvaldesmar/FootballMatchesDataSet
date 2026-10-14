"""Métricas y evaluación del clasificador 1X2."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

from .preprocessing import CLASS_NAMES, target_series
from .score import score_breakdown


def evaluate_predictions(
    y_true: pd.Series, predictions: np.ndarray, probabilities: np.ndarray | None = None
) -> dict[str, Any]:
    """Calcula métricas globales y una matriz de confusión serializable."""
    result: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "macro_f1": float(f1_score(y_true, predictions, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=[0, 1, 2]).tolist(),
    }
    if probabilities is not None:
        result["log_loss"] = float(log_loss(y_true, probabilities, labels=[0, 1, 2]))
        result["combined_score"] = score_breakdown(y_true, predictions, probabilities)[
            "combined_score"
        ]
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, predictions, labels=[0, 1, 2], zero_division=0
    )
    result["by_class"] = {
        label: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }
        for index, label in enumerate(CLASS_NAMES)
    }
    return result


def evaluate_model(model: Any, frame: pd.DataFrame) -> dict[str, Any]:
    """Evalúa un pipeline ya ajustado sobre un DataFrame ML."""
    predictions = np.asarray(model.predict(frame), dtype=int)
    probabilities = (
        np.asarray(model.predict_proba(frame), dtype=float)
        if hasattr(model, "predict_proba")
        else None
    )
    return evaluate_predictions(target_series(frame), predictions, probabilities)


def evaluate_by_season(model: Any, frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Genera métricas separadas para cada temporada del holdout."""
    result: dict[str, dict[str, Any]] = {}
    for season, group in frame.groupby("temporada", sort=False):
        result[str(season)] = evaluate_model(model, group)
    return result
