"""Orquestación del entrenamiento y persistencia del modelo."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .evaluate import evaluate_model
from .models import create_model
from .preprocessing import CLASS_NAMES, target_series
from .selection import SelectionReport, select_recent
from .split import temporal_split


def _report_dict(report: SelectionReport) -> dict[str, Any]:
    return {
        "input_rows": report.input_rows,
        "output_rows": report.output_rows,
        "discarded_rows": report.discarded_rows,
        "seasons": list(report.seasons),
        "min_year": report.min_year,
    }


def train_model(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    model_name: str = "logistic",
    min_season: str | None = "2000-01",
    last_seasons: int | None = None,
    test_seasons: int = 2,
    validation_seasons: int = 1,
) -> dict[str, Any]:
    """Selecciona la ventana reciente, entrena y guarda un artefacto joblib."""
    selected, selection = select_recent(frame, min_season=min_season, last_seasons=last_seasons)
    split = temporal_split(
        selected, test_seasons=test_seasons, validation_seasons=validation_seasons
    )
    model = create_model(model_name, split.train)
    model.fit(split.train, target_series(split.train))
    validation_metrics = (
        evaluate_model(model, split.validation) if not split.validation.empty else None
    )
    test_metrics = evaluate_model(model, split.test)
    artifact = {
        "artifact_version": 1,
        "model": model,
        "model_name": model_name,
        "classes": list(CLASS_NAMES),
        "created_at": datetime.now(UTC).isoformat(),
        "selection": _report_dict(selection),
        "train_seasons": list(split.train_seasons),
        "validation_seasons": list(split.validation_seasons),
        "test_seasons": list(split.test_seasons),
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, destination)
    return artifact


def load_artifact(path: str | Path) -> dict[str, Any]:
    """Carga y valida un artefacto persistido."""
    artifact = joblib.load(path)
    if not isinstance(artifact, dict) or "model" not in artifact:
        raise ValueError(f"Artefacto ML inválido: {path}")
    return artifact
