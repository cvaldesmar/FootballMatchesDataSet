"""Selección temporal: descarta histórico demasiado antiguo antes del ML."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .io import MLDatasetError, season_year


@dataclass(frozen=True)
class SelectionReport:
    """Resumen auditable del recorte temporal aplicado."""

    input_rows: int
    output_rows: int
    discarded_rows: int
    seasons: tuple[str, ...]
    min_year: int | None


def _with_year(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["_season_year"] = result["temporada"].map(season_year)
    return result


def _select(frame: pd.DataFrame, mask: pd.Series) -> tuple[pd.DataFrame, SelectionReport]:
    years = _with_year(frame)
    selected = (
        years.loc[mask.to_numpy()]
        .sort_values(["_season_year", "jornada"])
        .drop(columns="_season_year")
    )
    seasons = tuple(sorted(selected["temporada"].unique(), key=season_year))
    minimum = season_year(seasons[0]) if seasons else None
    report = SelectionReport(
        len(frame), len(selected), len(frame) - len(selected), seasons, minimum
    )
    return selected.reset_index(drop=True), report


def filter_by_min_season(
    frame: pd.DataFrame, min_season: str = "2000-01"
) -> tuple[pd.DataFrame, SelectionReport]:
    """Conserva temporadas cuyo año inicial es igual o posterior al corte."""
    cutoff = season_year(min_season)
    years = _with_year(frame)
    return _select(frame, years["_season_year"] >= cutoff)


def filter_last_seasons(
    frame: pd.DataFrame, last_seasons: int
) -> tuple[pd.DataFrame, SelectionReport]:
    """Conserva las N temporadas más recientes presentes en el CSV."""
    if last_seasons < 1:
        raise MLDatasetError("last_seasons debe ser mayor que cero")
    years = _with_year(frame)
    available = sorted(years["_season_year"].unique())
    if not available:
        raise MLDatasetError("No hay temporadas seleccionables")
    cutoff = available[-last_seasons] if last_seasons <= len(available) else available[0]
    return _select(frame, years["_season_year"] >= cutoff)


def select_recent(
    frame: pd.DataFrame,
    *,
    min_season: str | None = "2000-01",
    last_seasons: int | None = None,
) -> tuple[pd.DataFrame, SelectionReport]:
    """Aplica una ventana de recencia; ``last_seasons`` tiene prioridad."""
    if last_seasons is not None:
        return filter_last_seasons(frame, last_seasons)
    return filter_by_min_season(frame, min_season or "2000-01")
