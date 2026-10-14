"""Preprocesado reproducible de features y etiqueta 1X2."""

from __future__ import annotations

from typing import Final

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TARGET_COLUMN: Final = "resultado1X2"
TARGET_MAPPING: Final = {"1": 0, "X": 1, "2": 2}
CLASS_NAMES: Final = ("1", "X", "2")

# IDs y temporada se conservan para trazabilidad/split, no entran al modelo.
EXCLUDED_COLUMNS: Final = {TARGET_COLUMN, "temporada", "localId", "visitanteId"}
MISSING_AS_ABSENCE: Final = (
    "distanciaKm",
    "diferenciaValorMercado",
    "ratioValorMercado",
)


def add_missing_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Añade indicadores para los campos cuyo -1 significa ausencia."""
    result = frame.copy()
    for column in MISSING_AS_ABSENCE:
        if column not in result:
            continue
        result[f"es_ausente_{column}"] = (result[column] == -1).astype(float)
        result[column] = result[column].where(result[column] != -1)
    return result


def feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Selecciona features numéricas y elimina contexto no modelable."""
    result = add_missing_indicators(frame)
    columns = [column for column in result.columns if column not in EXCLUDED_COLUMNS]
    return result.loc[:, columns].apply(pd.to_numeric, errors="coerce")


def target_series(frame: pd.DataFrame) -> pd.Series:
    """Codifica la etiqueta canónica como 0=1, 1=X y 2=2."""
    target = frame[TARGET_COLUMN].map(TARGET_MAPPING)
    if target.isna().any():
        raise ValueError("La etiqueta contiene valores desconocidos")
    return target.astype(int)


def build_preprocessor(frame: pd.DataFrame) -> ColumnTransformer:
    """Construye el preprocesador sin ajustar estadísticas del conjunto externo."""
    columns = list(feature_frame(frame).columns)
    pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=False)),
            ("scaler", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        transformers=[("numeric", pipeline, columns)],
        remainder="drop",
        verbose_feature_names_out=False,
    )
