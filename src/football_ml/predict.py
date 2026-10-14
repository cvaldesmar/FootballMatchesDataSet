"""Inferencia usando un artefacto ML persistido."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .io import ML_COLUMNS, TARGET_COLUMN
from .preprocessing import CLASS_NAMES
from .train import load_artifact


def predict_frame(artifact: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Devuelve clase predicha y probabilidades para cada fila."""
    model = artifact["model"]
    predictions = model.predict(frame)
    probabilities = model.predict_proba(frame)
    result = pd.DataFrame({"prediccion": [CLASS_NAMES[int(value)] for value in predictions]})
    for index, label in enumerate(CLASS_NAMES):
        result[f"probabilidad_{label}"] = probabilities[:, index]
    return result


def predict_csv(model_path: str, input_path: str, output_path: str | None = None) -> pd.DataFrame:
    """Predice un CSV ML sin requerir que contenga la etiqueta."""
    frame = pd.read_csv(input_path, sep=";")
    missing = [
        column for column in ML_COLUMNS if column not in frame.columns and column != TARGET_COLUMN
    ]
    if missing:
        raise ValueError(f"Faltan columnas para predecir: {', '.join(missing)}")
    artifact = load_artifact(model_path)
    result = predict_frame(artifact, frame)
    if output_path:
        result.to_csv(output_path, sep=";", index=False)
    return result
