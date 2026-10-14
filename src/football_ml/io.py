"""Carga y validación del artefacto CSV preparado para ML."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from src.football_dataset.ml_features import ML_COLUMNS, ML_METADATA_PREFIX

TARGET_COLUMN: Final = "resultado1X2"
TARGET_VALUES: Final = ("1", "X", "2")


class MLDatasetError(ValueError):
    """Error de estructura o contenido del dataset de ML."""


def load_ml_dataset(path: str | Path) -> pd.DataFrame:
    """Carga un CSV ML validando metadato, columnas y etiqueta."""
    source = Path(path)
    if not source.is_file():
        raise MLDatasetError(f"No existe el dataset ML: {source}")

    with source.open(encoding="utf-8", newline="") as file:
        metadata = file.readline().rstrip("\r\n")
    if metadata != ML_METADATA_PREFIX:
        raise MLDatasetError(
            f"Metadato incompatible en {source}: se esperaba {ML_METADATA_PREFIX!r}"
        )

    frame = pd.read_csv(
        source,
        sep=";",
        skiprows=1,
        dtype={"temporada": "string", TARGET_COLUMN: "string"},
    )
    missing = [column for column in ML_COLUMNS if column not in frame.columns]
    if missing:
        raise MLDatasetError(f"Faltan columnas ML obligatorias: {', '.join(missing)}")
    if frame.empty:
        raise MLDatasetError(f"El dataset ML está vacío: {source}")

    frame = frame.loc[:, ML_COLUMNS].copy()
    frame[TARGET_COLUMN] = frame[TARGET_COLUMN].str.strip()
    invalid = sorted(set(frame[TARGET_COLUMN].dropna()) - set(TARGET_VALUES))
    if invalid or frame[TARGET_COLUMN].isna().any():
        values = ", ".join(invalid) if invalid else "vacíos"
        raise MLDatasetError(f"Valores inválidos en {TARGET_COLUMN}: {values}")

    for column in ML_COLUMNS:
        if column not in {"temporada", TARGET_COLUMN}:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame["temporada"].isna().any():
        raise MLDatasetError("Hay temporadas vacías en el dataset ML")
    return frame.reset_index(drop=True)


def season_year(value: object) -> int:
    """Devuelve el año inicial de una temporada, por ejemplo 2021-22 -> 2021."""
    text = str(value).strip()
    try:
        return int(text.split("-", 1)[0])
    except (TypeError, ValueError, IndexError) as error:
        raise MLDatasetError(f"Temporada inválida: {value!r}") from error
