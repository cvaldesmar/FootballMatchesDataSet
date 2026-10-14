"""Búsqueda Optuna de modelos e hiperparámetros con validación temporal."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .models import RANDOM_STATE, create_model
from .walk_forward import walk_forward_evaluate


def suggest_params(trial: Any, model_name: str) -> dict[str, Any]:
    """Sugiere hiperparámetros para un modelo concreto."""
    if model_name == "logistic":
        return {
            "C": trial.suggest_float("C", 1e-3, 20.0, log=True),
            "solver": trial.suggest_categorical("solver", ["lbfgs", "saga"]),
            "class_weight": trial.suggest_categorical("class_weight", ["balanced", None]),
        }
    if model_name == "random-forest":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 15),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
        }
    if model_name == "gradient-boosting":
        return {
            "max_iter": trial.suggest_int("max_iter", 100, 500, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_leaf_nodes": trial.suggest_int("max_leaf_nodes", 7, 63),
            "l2_regularization": trial.suggest_float("l2_regularization", 1e-4, 10.0, log=True),
        }
    if model_name == "xgboost":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 500, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 10),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 20.0, log=True),
        }
    if model_name == "lightgbm":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 500, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 63),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 20.0, log=True),
        }
    raise ValueError(f"Modelo sin espacio de búsqueda: {model_name}")


def _factory(model_name: str):
    def build(frame: pd.DataFrame, params: dict[str, Any]):
        return create_model(model_name, frame, params)

    return build


def tune_model(
    frame: pd.DataFrame,
    model_name: str,
    *,
    n_trials: int = 20,
    min_train_rounds: int = 10,
    max_validation_rounds: int | None = None,
    max_train_rounds: int | None = None,
    seed: int = RANDOM_STATE,
) -> dict[str, Any]:
    """Optimiza un modelo y devuelve el mejor trial con walk-forward."""
    try:
        import optuna
    except ImportError as error:
        raise RuntimeError("Instala requirements-ml.txt para usar Optuna") from error

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=seed)
    pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=3)
    study = optuna.create_study(direction="maximize", sampler=sampler, pruner=pruner)

    def objective(trial: Any) -> float:
        params = suggest_params(trial, model_name)
        result = walk_forward_evaluate(
            frame,
            _factory(model_name),
            params,
            min_train_rounds=min_train_rounds,
            max_train_rounds=max_train_rounds,
            max_validation_rounds=max_validation_rounds,
            trial=trial,
        )
        trial.set_user_attr("metrics", result.metrics)
        trial.set_user_attr("rounds", result.rows_evaluated)
        return result.metrics["combined_score"]

    study.optimize(objective, n_trials=n_trials)
    best = study.best_trial
    best_result = walk_forward_evaluate(
        frame,
        _factory(model_name),
        dict(best.params),
        min_train_rounds=min_train_rounds,
        max_train_rounds=max_train_rounds,
        max_validation_rounds=max_validation_rounds,
    )
    return {
        "model_name": model_name,
        "params": dict(best.params),
        "metrics": best_result.metrics,
        "rows_evaluated": best_result.rows_evaluated,
        "rounds": list(best_result.rounds),
        "n_trials": n_trials,
        "study": study,
    }


def tune_catalog(
    frame: pd.DataFrame,
    model_names: tuple[str, ...],
    *,
    n_trials: int = 20,
    min_train_rounds: int = 10,
    max_validation_rounds: int | None = None,
    max_train_rounds: int | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Optimiza todos los modelos disponibles y persiste el campeón."""
    results = [
        tune_model(
            frame,
            name,
            n_trials=n_trials,
            min_train_rounds=min_train_rounds,
            max_validation_rounds=max_validation_rounds,
            max_train_rounds=max_train_rounds,
        )
        for name in model_names
    ]
    winner = max(results, key=lambda result: result["metrics"]["combined_score"])
    final_model = create_model(winner["model_name"], frame, winner["params"])
    from .preprocessing import target_series

    final_model.fit(frame, target_series(frame))
    artifact = {
        "artifact_version": 2,
        "model": final_model,
        "model_name": winner["model_name"],
        "params": winner["params"],
        "walk_forward_metrics": winner["metrics"],
        "catalog_results": [
            {key: value for key, value in result.items() if key != "study"} for result in results
        ],
        "created_at": datetime.now(UTC).isoformat(),
        "trained_until": str(frame["temporada"].iloc[-1]),
    }
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, destination)
    return artifact
