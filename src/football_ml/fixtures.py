"""Carga y validación de fixtures futuras sin resultado conocido."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("division", "temporada", "jornada", "matchDate", "localId", "visitanteId")


def load_fixtures(path: str | Path) -> pd.DataFrame:
    """Lee fixtures futuras; no permite columnas de resultado ni goles."""
    source = Path(path)
    frame = pd.read_csv(source, sep=";")
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Faltan columnas de fixtures: {', '.join(missing)}")
    forbidden = {"resultado1X2", "golesLocal", "golesVisitante", "golDiff"}
    present = sorted(forbidden & set(frame.columns))
    if present:
        raise ValueError(f"Las fixtures no pueden incluir resultados: {', '.join(present)}")
    result = frame.copy()
    result["matchDate"] = pd.to_datetime(result["matchDate"], errors="raise").dt.date
    for column in ("division", "jornada", "localId", "visitanteId"):
        result[column] = pd.to_numeric(result[column], errors="raise").astype(int)
    if result.empty:
        raise ValueError("El fichero de fixtures está vacío")
    if (result["localId"] == result["visitanteId"]).any():
        raise ValueError("Una fixture no puede enfrentar un equipo consigo mismo")
    return result


def load_historical_source(path: str | Path) -> pd.DataFrame:
    """Carga el CSV histórico v3 saltando su línea de metadato."""
    source = Path(path)
    with source.open(encoding="utf-8", newline="") as file:
        metadata = file.readline().rstrip("\r\n")
    if not metadata.startswith("# football_dataset_schema="):
        raise ValueError(f"CSV histórico sin metadato de esquema: {source}")
    return pd.read_csv(source, sep=";", skiprows=1, parse_dates=["matchDate"])


def cutoff_history(frame: pd.DataFrame, as_of: date) -> pd.DataFrame:
    """Conserva únicamente partidos finalizados en o antes de ``as_of``."""
    dates = pd.to_datetime(frame["matchDate"], errors="raise").dt.date
    return frame.loc[dates <= as_of].copy().reset_index(drop=True)
