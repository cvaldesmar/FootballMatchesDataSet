"""Estrategias comparables para predicción 1X2."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .models import create_model
from .poisson import Poisson1X2Classifier
from .preprocessing import target_series
from .staged import Staged1X2Classifier

STRATEGY_NAMES = ("multiclass", "staged", "poisson")


def train_strategy(name: str, frame: pd.DataFrame, params: dict[str, Any] | None = None) -> Any:
    """Entrena una estrategia y devuelve un estimador con ``predict_proba``."""
    options = params or {}
    if name == "multiclass":
        model_name = options.pop("model_name", "logistic")
        model = create_model(model_name, frame, options)
        model.fit(frame, target_series(frame))
        return model
    if name == "staged":
        model = Staged1X2Classifier(
            C=float(options.get("C", 1.0)),
            class_weight=options.get("class_weight", "balanced"),
        )
        model.fit(frame, target_series(frame))
        return model
    if name == "poisson":
        model = Poisson1X2Classifier(
            alpha=float(options.get("alpha", 1.0)),
            max_goals=int(options.get("max_goals", 10)),
        )
        model.fit_goals(frame, frame["golesLocal"], frame["golesVisitante"])
        return model
    raise ValueError(f"Estrategia desconocida {name!r}; disponibles: {STRATEGY_NAMES}")


def strategy_factory(name: str):
    """Devuelve una función compatible con ``walk_forward_evaluate``."""

    def train_step(frame: pd.DataFrame, params: dict[str, Any]) -> Any:
        return train_strategy(name, frame, dict(params))

    return train_step
