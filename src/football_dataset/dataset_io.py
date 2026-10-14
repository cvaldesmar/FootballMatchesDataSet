"""Persistencia explícita del dataset; no depende de variables globales."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Protocol, TextIO, cast

from .context import ExecutionContext
from .FootballClasses import Partido

SCHEMA_VERSION = 3
SCHEMA_METADATA_PREFIX = f"# football_dataset_schema={SCHEMA_VERSION}"

class SeasonLike(Protocol):
    jornadas: dict[int, dict[int, Partido]]


HEADERS = [
    "idPartido",
    "division",
    "temporada",
    "jornada",
    "matchDate",
    "arbitroName",
    "arbitroId",
    "localName",
    "localId",
    "localMarketValue",
    "puntosLocal",
    "golesafavorlocal",
    "golesencontralocal",
    "posicionLocal",
    "visitanteName",
    "visitanteId",
    "visitanteMarketValue",
    "puntosVisitante",
    "posicionVisitante",
    "diferenciaPuntos",
    "golesafavorvisitante",
    "golesencontravisitante",
    "rachaLocal",
    "rachaVisitante",
    "formaLocal",
    "formaVisitante",
    "h2hLocalWins",
    "h2hDraws",
    "h2hAwayWins",
    "h2hMatches",
    "campeonId",
    "descensoConfirmadoLocal",
    "descensoConfirmadoVisitante",
    "presionLocal",
    "presionVisitante",
    "rivalidad",
    "distanciaKm",
    "golesLocal",
    "golesVisitante",
    "golDiff",
    "resultado1X2",
]


def _match_row(match: Partido) -> dict[str, object]:
    return {header: getattr(match, header, "") for header in HEADERS}


def _write_header(file: TextIO) -> None:
    file.write(SCHEMA_METADATA_PREFIX + "\n")
    csv.DictWriter(file, fieldnames=HEADERS, delimiter=";").writeheader()


def write_csv_header(path: str | Path) -> None:
    """Crea o reinicia el CSV con metadato y cabecera versionados."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        _write_header(file)


def _ensure_versioned_header(file: TextIO, destination: Path) -> None:
    if destination.stat().st_size == 0:
        _write_header(file)
        return
    file.seek(0)
    first_line = file.readline().rstrip("\r\n")
    if first_line != SCHEMA_METADATA_PREFIX:
        raise ValueError(
            f"El CSV {destination} no tiene metadato de esquema compatible "
            f"(se esperaba {SCHEMA_METADATA_PREFIX!r})"
        )
    header = file.readline().rstrip("\r\n").split(";")
    if header != HEADERS:
        raise ValueError(
            f"Cabecera CSV incompatible con el esquema {SCHEMA_VERSION}: {destination}"
        )
    file.seek(0, 2)


def append_season(path: str | Path, season: object) -> int:
    """Añade una temporada validada sin duplicar metadato ni cabecera."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    season_data = cast(SeasonLike, season)
    matches = [
        match for jornada in season_data.jornadas.values() for match in jornada.values()
    ]
    with destination.open("a+", encoding="utf-8", newline="") as file:
        _ensure_versioned_header(file, destination)
        writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter=";", extrasaction="ignore")
        for match in matches:
            writer.writerow(_match_row(match))
    return len(matches)


def iter_matches(context: ExecutionContext) -> Any:
    for seasons in context.all_seasons_info.values():
        for season in seasons.values():
            for matches in season.jornadas.values():
                yield from matches.values()


def save_all_seasons(context: ExecutionContext, path: str | Path | None = None) -> int:
    destination = Path(path or context.output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8", newline="") as file:
        _write_header(file)
        writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter=";", extrasaction="ignore")
        for match in iter_matches(context):
            writer.writerow(_match_row(match))
            count += 1
    return count
