"""Flujo operativo para entrenar y predecir la próxima jornada."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.football_dataset.ml_features import transform_rows

from .fixtures import cutoff_history, load_fixtures, load_historical_source
from .predict import predict_frame
from .snapshots import build_fixture_features
from .train import load_artifact, train_model


def run_next_round(
    history_path: str | Path,
    fixtures_path: str | Path,
    model_path: str | Path,
    *,
    as_of: date,
    min_season: str | None = "2000-01",
    last_seasons: int | None = None,
    model_name: str = "logistic",
    output_path: str | Path | None = None,
    retrain: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Usa el campeón persistido o reentrena explícitamente antes de predecir."""
    source = load_historical_source(history_path)
    fixtures = load_fixtures(fixtures_path)
    if (fixtures["matchDate"] <= as_of).any():
        raise ValueError("Todas las fixtures deben ser posteriores a as_of")

    if Path(model_path).is_file() and not retrain:
        artifact = load_artifact(model_path)
    else:
        history = cutoff_history(source, as_of)
        training_rows = transform_rows(history.astype(object).to_dict("records"))
        training_frame = pd.DataFrame(training_rows)
        artifact = train_model(
            training_frame,
            model_path,
            model_name=model_name,
            min_season=min_season,
            last_seasons=last_seasons,
        )
    fixture_features = build_fixture_features(source, fixtures, as_of)
    predictions = predict_frame(artifact, fixture_features)
    identity = fixtures[
        ["division", "temporada", "jornada", "matchDate", "localId", "visitanteId"]
    ].reset_index(drop=True)
    result = pd.concat([identity, predictions], axis=1)
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(destination, sep=";", index=False)
    return result, artifact
