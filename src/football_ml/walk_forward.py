"""Validación walk-forward cronológica por jornada."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .preprocessing import target_series
from .score import score_breakdown


@dataclass(frozen=True)
class WalkForwardResult:
    """Resultado agregado y detalle de una evaluación walk-forward."""

    metrics: dict[str, float]
    rounds: tuple[dict[str, Any], ...]
    rows_evaluated: int


def ordered_rounds(frame: pd.DataFrame) -> list[tuple[str, int]]:
    """Devuelve rondas estables ordenadas por temporada y jornada."""
    values = frame[["temporada", "jornada"]].drop_duplicates().copy()
    values["season_year"] = values["temporada"].astype(str).str.split("-", n=1).str[0].astype(int)
    values["jornada"] = pd.to_numeric(values["jornada"], errors="raise").astype(int)
    values = values.sort_values(["season_year", "jornada"])
    return [(str(row.temporada), int(row.jornada)) for row in values.itertuples()]


def walk_forward_evaluate(
    frame: pd.DataFrame,
    model_factory: Callable[[pd.DataFrame, dict[str, Any]], Any],
    params: dict[str, Any] | None = None,
    *,
    min_train_rounds: int = 10,
    max_train_rounds: int | None = None,
    max_validation_rounds: int | None = None,
    trial: Any | None = None,
) -> WalkForwardResult:
    """Entrena antes de cada ronda y evalúa solo la ronda siguiente.

    ``model_factory`` recibe el DataFrame de entrenamiento y los parámetros del
    trial. El modelo se ajusta exclusivamente con rondas anteriores.
    """
    params = params or {}
    rounds = ordered_rounds(frame)
    if len(rounds) <= min_train_rounds:
        raise ValueError("No hay suficientes rondas para walk-forward")
    start = min_train_rounds
    stop = len(rounds)
    if max_validation_rounds is not None:
        stop = min(stop, start + max_validation_rounds)

    true_parts: list[np.ndarray] = []
    prediction_parts: list[np.ndarray] = []
    probability_parts: list[np.ndarray] = []
    details: list[dict[str, Any]] = []
    total_steps = stop - start
    for step, round_key in enumerate(rounds[start:stop]):
        if trial is not None:
            print(
                f"[tune] {trial.study.study_name if trial.study else 'trial'} "
                f"trial={trial.number + 1} ronda={step + 1}/{total_steps} "
                f"({round_key[0]} jornada {round_key[1]})",
                flush=True,
            )
        train_rounds = rounds[: start + step]
        if max_train_rounds is not None:
            train_rounds = train_rounds[-max_train_rounds:]
        train_mask = frame.set_index(["temporada", "jornada"]).index.isin(train_rounds)
        valid_mask = frame.set_index(["temporada", "jornada"]).index == round_key
        train = frame.loc[train_mask].reset_index(drop=True)
        valid = frame.loc[valid_mask].reset_index(drop=True)
        model = model_factory(train, params)
        model.fit(train, target_series(train))
        predictions = np.asarray(model.predict(valid), dtype=int)
        probabilities = np.asarray(model.predict_proba(valid), dtype=float)
        true = target_series(valid).to_numpy()
        true_parts.append(true)
        prediction_parts.append(predictions)
        probability_parts.append(probabilities)
        partial = score_breakdown(
            np.concatenate(true_parts),
            np.concatenate(prediction_parts),
            np.vstack(probability_parts),
        )
        detail = {"temporada": round_key[0], "jornada": round_key[1], **partial}
        details.append(detail)
        if trial is not None:
            trial.report(partial["combined_score"], step)
            if trial.should_prune():
                import optuna

                raise optuna.TrialPruned()

    y_true = np.concatenate(true_parts)
    predictions = np.concatenate(prediction_parts)
    probabilities = np.vstack(probability_parts)
    return WalkForwardResult(
        metrics=score_breakdown(y_true, predictions, probabilities),
        rounds=tuple(details),
        rows_evaluated=len(y_true),
    )
