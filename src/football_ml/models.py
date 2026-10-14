"""Fábricas parametrizables de clasificadores supervisados."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from sklearn.base import ClassifierMixin
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from .preprocessing import add_missing_indicators, build_preprocessor

RANDOM_STATE: Final = 42
ModelFactory = Callable[[object, dict[str, Any] | None], ClassifierMixin]


def _pipeline(frame: object, classifier: ClassifierMixin) -> ClassifierMixin:
    return Pipeline(
        steps=[
            ("missing_indicators", FunctionTransformer(add_missing_indicators)),
            ("preprocessor", build_preprocessor(frame)),
            ("classifier", classifier),
        ]
    )


def logistic_model(frame: object, params: dict[str, Any] | None = None) -> ClassifierMixin:
    options = {"max_iter": 1000, "class_weight": "balanced", "random_state": RANDOM_STATE}
    options.update(params or {})
    return _pipeline(frame, LogisticRegression(**options))


def random_forest_model(frame: object, params: dict[str, Any] | None = None) -> ClassifierMixin:
    options = {
        "n_estimators": 300,
        "min_samples_leaf": 5,
        "class_weight": "balanced",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }
    options.update(params or {})
    return _pipeline(frame, RandomForestClassifier(**options))


def gradient_boosting_model(frame: object, params: dict[str, Any] | None = None) -> ClassifierMixin:
    options = {
        "max_iter": 250,
        "learning_rate": 0.05,
        "max_leaf_nodes": 15,
        "l2_regularization": 1.0,
        "random_state": RANDOM_STATE,
    }
    options.update(params or {})
    return _pipeline(frame, HistGradientBoostingClassifier(**options))


def xgboost_model(frame: object, params: dict[str, Any] | None = None) -> ClassifierMixin:
    """Construye XGBoost bajo demanda, sin importar la dependencia al importar el módulo."""
    try:
        from xgboost import XGBClassifier
    except ImportError as error:
        raise RuntimeError("Instala requirements-ml.txt para usar XGBoost") from error
    options = {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": 4,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }
    options.update(params or {})
    return _pipeline(frame, XGBClassifier(**options))


def lightgbm_model(frame: object, params: dict[str, Any] | None = None) -> ClassifierMixin:
    """Construye LightGBM bajo demanda, sin importar la dependencia al importar el módulo."""
    try:
        from lightgbm import LGBMClassifier
    except ImportError as error:
        raise RuntimeError("Instala requirements-ml.txt para usar LightGBM") from error
    options = {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "objective": "multiclass",
        "num_class": 3,
        "class_weight": "balanced",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
        "verbosity": -1,
    }
    options.update(params or {})
    return _pipeline(frame, LGBMClassifier(**options))


MODEL_FACTORIES: Final[dict[str, ModelFactory]] = {
    "logistic": logistic_model,
    "random-forest": random_forest_model,
    "gradient-boosting": gradient_boosting_model,
    "xgboost": xgboost_model,
    "lightgbm": lightgbm_model,
}


def create_model(name: str, frame: object, params: dict[str, Any] | None = None) -> ClassifierMixin:
    """Crea el modelo solicitado con los hiperparámetros indicados."""
    try:
        factory = MODEL_FACTORIES[name]
    except KeyError as error:
        available = ", ".join(sorted(MODEL_FACTORIES))
        raise ValueError(f"Modelo desconocido {name!r}; disponibles: {available}") from error
    return factory(frame, params)
