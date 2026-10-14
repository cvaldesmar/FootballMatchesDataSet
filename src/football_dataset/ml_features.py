"""Generación offline de un dataset simplificado y enriquecido para ML 1X2."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .dataset_io import HEADERS, SCHEMA_METADATA_PREFIX

ML_METADATA_PREFIX = "# football_dataset_ml=1"
DROP_COLUMNS = {
    "idPartido",
    "localName",
    "visitanteName",
    "localId",
    "visitanteId",
    "arbitroName",
    "arbitroId",
    "matchDate",
}
ML_COLUMNS = [
    "division",
    "temporada",
    "jornada",
    "localId",
    "visitanteId",
    "diferenciaPuntos",
    "diferenciaPosicion",
    "diferenciaGolesNeta",
    "rachaLocal",
    "rachaVisitante",
    "h2hMatches",
    "h2hBalance",
    "campeonDecidido",
    "descensoConfirmadoLocal",
    "descensoConfirmadoVisitante",
    "presionLocal",
    "presionVisitante",
    "rivalidad",
    "distanciaKm",
    "diferenciaValorMercado",
    "ratioValorMercado",
    "golesFavor5Local",
    "golesContra5Local",
    "golesFavor10Local",
    "golesContra10Local",
    "golesFavor5Visitante",
    "golesContra5Visitante",
    "golesFavor10Visitante",
    "golesContra10Visitante",
    "rachaLocalCasa",
    "rachaVisitanteFuera",
    "partidosCasaLocal",
    "partidosFueraVisitante",
    "diasDescansoLocal",
    "diasDescansoVisitante",
    "partidos7DiasLocal",
    "partidos7DiasVisitante",
    "diferenciaDescanso",
    "sobreRendimientoLocal",
    "sobreRendimientoVisitante",
    "golesLocal",
    "golesVisitante",
    "resultado1X2",
]


def _number(row: dict[str, Any], column: str, default: float = -1.0) -> float:
    try:
        return float(row.get(column, ""))
    except (TypeError, ValueError):
        return default


def _match_date(row: dict[str, Any]) -> date | None:
    value = row.get("matchDate")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _rolling(
    history: list[tuple[date | None, float, float, int]], size: int
) -> tuple[float, float]:
    recent = history[-size:]
    if not recent:
        return 0.0, 0.0
    return (
        sum(item[1] for item in recent) / len(recent),
        sum(item[2] for item in recent) / len(recent),
    )


def _streak(history: list[tuple[date | None, float, float, int]]) -> float:
    return float(sum(item[3] for item in history[-5:]))


def _rest_days(history: list[tuple[date | None, float, float, int]], current: date | None) -> float:
    if current is None or not history or history[-1][0] is None:
        return -1.0
    return float(max(0, (current - history[-1][0]).days))


def _matches_last_days(
    history: list[tuple[date | None, float, float, int]], current: date | None, days: int = 7
) -> int:
    if current is None:
        return 0
    return sum(
        1 for item in history if item[0] is not None and 0 < (current - item[0]).days <= days
    )


def _new_features(
    source: dict[str, Any],
    local_history: list[tuple[date | None, float, float, int]],
    away_history: list[tuple[date | None, float, float, int]],
    local_home_history: list[tuple[date | None, float, float, int]],
    away_away_history: list[tuple[date | None, float, float, int]],
    market_overperformance: dict[int, float],
) -> dict[str, str]:
    current_date = _match_date(source)
    local_5_for, local_5_against = _rolling(local_history, 5)
    local_10_for, local_10_against = _rolling(local_history, 10)
    away_5_for, away_5_against = _rolling(away_history, 5)
    away_10_for, away_10_against = _rolling(away_history, 10)
    local_id = int(_number(source, "localId", 0))
    away_id = int(_number(source, "visitanteId", 0))
    local_market = _number(source, "localMarketValue")
    away_market = _number(source, "visitanteMarketValue")
    total_market = local_market + away_market
    local_expected = 3.0 * local_market / total_market if total_market > 0 else 1.5
    away_expected = 3.0 * away_market / total_market if total_market > 0 else 1.5
    return {
        "golesFavor5Local": str(local_5_for),
        "golesContra5Local": str(local_5_against),
        "golesFavor10Local": str(local_10_for),
        "golesContra10Local": str(local_10_against),
        "golesFavor5Visitante": str(away_5_for),
        "golesContra5Visitante": str(away_5_against),
        "golesFavor10Visitante": str(away_10_for),
        "golesContra10Visitante": str(away_10_against),
        "rachaLocalCasa": str(_streak(local_home_history)),
        "rachaVisitanteFuera": str(_streak(away_away_history)),
        "partidosCasaLocal": str(len(local_home_history)),
        "partidosFueraVisitante": str(len(away_away_history)),
        "diasDescansoLocal": str(_rest_days(local_history, current_date)),
        "diasDescansoVisitante": str(_rest_days(away_history, current_date)),
        "partidos7DiasLocal": str(_matches_last_days(local_history, current_date)),
        "partidos7DiasVisitante": str(_matches_last_days(away_history, current_date)),
        "diferenciaDescanso": str(
            _rest_days(local_history, current_date) - _rest_days(away_history, current_date)
        ),
        "sobreRendimientoLocal": str(market_overperformance.get(local_id, 0.0) - local_expected),
        "sobreRendimientoVisitante": str(market_overperformance.get(away_id, 0.0) - away_expected),
    }


def transform_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Crea features derivadas usando snapshots previos al inicio de cada jornada."""
    source_rows = list(rows)
    indexed = list(enumerate(source_rows))
    indexed.sort(
        key=lambda item: (
            int(str(item[1].get("temporada", "0")).split("-", 1)[0]),
            int(_number(item[1], "division", 0)),
            int(_number(item[1], "jornada", 0)),
            _match_date(item[1]) or date.min,
            item[0],
        )
    )
    histories: dict[tuple[int, str, int], list[tuple[date | None, float, float, int]]] = (
        defaultdict(list)
    )
    home_histories: dict[tuple[int, str, int], list[tuple[date | None, float, float, int]]] = (
        defaultdict(list)
    )
    away_histories: dict[tuple[int, str, int], list[tuple[date | None, float, float, int]]] = (
        defaultdict(list)
    )
    market_overperformance: dict[tuple[int, str, int], float] = defaultdict(float)
    transformed: dict[int, dict[str, str]] = {}
    position = 0
    while position < len(indexed):
        row_position = position
        division = int(_number(indexed[position][1], "division", 0))
        season = str(indexed[position][1].get("temporada", ""))
        jornada = int(_number(indexed[position][1], "jornada", 0))
        group: list[tuple[int, dict[str, str]]] = []
        while row_position < len(indexed):
            original_index, row = indexed[row_position]
            if (
                int(_number(row, "division", 0)) != division
                or str(row.get("temporada", "")) != season
                or int(_number(row, "jornada", 0)) != jornada
            ):
                break
            group.append((original_index, row))
            row_position += 1
        local_snapshots = {key: list(value) for key, value in histories.items()}
        home_snapshots = {key: list(value) for key, value in home_histories.items()}
        away_snapshots = {key: list(value) for key, value in away_histories.items()}
        market_snapshots = dict(market_overperformance)
        for original_index, source in group:
            local_id = int(_number(source, "localId", 0))
            away_id = int(_number(source, "visitanteId", 0))
            local_key = (division, season, local_id)
            away_key = (division, season, away_id)
            local_history = local_snapshots.get(local_key, [])
            away_history = local_snapshots.get(away_key, [])
            row = {column: source.get(column, "") for column in ML_COLUMNS if column in source}
            local_market = _number(source, "localMarketValue")
            away_market = _number(source, "visitanteMarketValue")
            local_goal_balance = _number(source, "golesafavorlocal") - _number(
                source, "golesencontralocal"
            )
            away_goal_balance = _number(source, "golesafavorvisitante") - _number(
                source, "golesencontravisitante"
            )
            row.update(
                {
                    "diferenciaValorMercado": str(local_market - away_market),
                    "ratioValorMercado": str(
                        local_market / away_market
                        if away_market > 0 and local_market >= 0
                        else -1.0
                    ),
                    "diferenciaPosicion": str(
                        _number(source, "posicionVisitante") - _number(source, "posicionLocal")
                    ),
                    "diferenciaGolesNeta": str(local_goal_balance - away_goal_balance),
                    "h2hBalance": str(
                        _number(source, "h2hLocalWins") - _number(source, "h2hAwayWins")
                    ),
                    "campeonDecidido": str(1 if _number(source, "campeonId") >= 0 else 0),
                }
            )
            row.update(
                _new_features(
                    source,
                    local_history,
                    away_history,
                    home_snapshots.get(local_key, []),
                    away_snapshots.get(away_key, []),
                    {
                        team_id[2]: value
                        for team_id, value in market_snapshots.items()
                        if team_id[0] == division and team_id[1] == season
                    },
                )
            )
            transformed[original_index] = {column: row.get(column, "") for column in ML_COLUMNS}
        for _, source in group:
            local_id = int(_number(source, "localId", 0))
            away_id = int(_number(source, "visitanteId", 0))
            current_date = _match_date(source)
            home_goals = _number(source, "golesLocal", 0.0)
            away_goals = _number(source, "golesVisitante", 0.0)
            outcome = 1 if home_goals > away_goals else -1 if home_goals < away_goals else 0
            local_points = 3 if outcome > 0 else 1 if outcome == 0 else 0
            away_points = 3 if outcome < 0 else 1 if outcome == 0 else 0
            local_key = (division, season, local_id)
            away_key = (division, season, away_id)
            local_market = _number(source, "localMarketValue")
            away_market = _number(source, "visitanteMarketValue")
            total_market = local_market + away_market
            local_expected = 3.0 * local_market / total_market if total_market > 0 else 1.5
            away_expected = 3.0 * away_market / total_market if total_market > 0 else 1.5
            histories[local_key].append(
                (
                    current_date,
                    home_goals,
                    away_goals,
                    1 if outcome > 0 else -1 if outcome < 0 else 0,
                )
            )
            histories[away_key].append(
                (
                    current_date,
                    away_goals,
                    home_goals,
                    1 if outcome < 0 else -1 if outcome > 0 else 0,
                )
            )
            home_histories[local_key].append(
                (
                    current_date,
                    home_goals,
                    away_goals,
                    1 if outcome > 0 else -1 if outcome < 0 else 0,
                )
            )
            away_histories[away_key].append(
                (
                    current_date,
                    away_goals,
                    home_goals,
                    1 if outcome < 0 else -1 if outcome > 0 else 0,
                )
            )
            market_overperformance[local_key] += local_points - local_expected
            market_overperformance[away_key] += away_points - away_expected
        position = row_position
    return [transformed[index] for index in range(len(source_rows))]


def _read_source(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    with source.open(encoding="utf-8", newline="") as file:
        if file.readline().rstrip("\r\n") != SCHEMA_METADATA_PREFIX:
            raise ValueError(f"CSV sin esquema v3: {source}")
        reader = csv.DictReader(file, delimiter=";")
        if reader.fieldnames != HEADERS:
            raise ValueError(f"Cabecera CSV incompatible: {source}")
        return list(reader)


def build_ml_features(input_path: str | Path, output_path: str | Path) -> int:
    """Genera el artefacto ML sin modificar el dataset fuente."""
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    if source == destination:
        raise ValueError("El dataset ML debe escribirse en una ruta distinta al dataset fuente")
    rows = transform_rows(_read_source(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        file.write(ML_METADATA_PREFIX + "\n")
        writer = csv.DictWriter(file, fieldnames=ML_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera features simplificadas para ML")
    parser.add_argument("--input", required=True, help="CSV v3 fuente")
    parser.add_argument("--output", required=True, help="CSV ML derivado")
    args = parser.parse_args()
    print(f"Filas transformadas: {build_ml_features(args.input, args.output)}")


if __name__ == "__main__":
    main()
