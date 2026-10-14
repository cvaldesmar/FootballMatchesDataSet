"""Divisiones cronológicas por temporada, sin barajar observaciones."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .io import MLDatasetError, season_year


@dataclass(frozen=True)
class TemporalSplit:
    """Particiones y temporadas correspondientes."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    train_seasons: tuple[str, ...]
    validation_seasons: tuple[str, ...]
    test_seasons: tuple[str, ...]


def _ordered_seasons(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["temporada"].astype(str).unique(), key=season_year)


def temporal_split(
    frame: pd.DataFrame,
    *,
    test_seasons: int = 2,
    validation_seasons: int = 1,
) -> TemporalSplit:
    """Separa temporadas antiguas para train y recientes para holdout."""
    if test_seasons < 1 or validation_seasons < 0:
        raise MLDatasetError("test_seasons debe ser >= 1 y validation_seasons >= 0")
    seasons = _ordered_seasons(frame)
    required = test_seasons + validation_seasons + 1
    if len(seasons) < required:
        raise MLDatasetError(
            f"Se necesitan al menos {required} temporadas y solo hay {len(seasons)}"
        )

    test = tuple(seasons[-test_seasons:])
    validation_end = len(seasons) - test_seasons
    validation_start = max(0, validation_end - validation_seasons)
    validation = tuple(seasons[validation_start:validation_end])
    train = tuple(seasons[:validation_start])

    ordered = frame.assign(_season_order=frame["temporada"].map(season_year)).sort_values(
        ["_season_order", "jornada"]
    )
    train_frame = ordered[ordered["temporada"].isin(train)]
    validation_frame = ordered[ordered["temporada"].isin(validation)]
    test_frame = ordered[ordered["temporada"].isin(test)]
    return TemporalSplit(
        train=train_frame.drop(columns="_season_order").reset_index(drop=True),
        validation=validation_frame.drop(columns="_season_order").reset_index(drop=True),
        test=test_frame.drop(columns="_season_order").reset_index(drop=True),
        train_seasons=train,
        validation_seasons=validation,
        test_seasons=test,
    )
