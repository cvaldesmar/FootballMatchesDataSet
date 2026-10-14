"""Construcción de features prepartido para fixtures futuras."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import pandas as pd

from src.football_dataset.ml_features import ML_COLUMNS

from .fixtures import cutoff_history


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _team_state(history: pd.DataFrame, team_id: int, home: bool) -> dict[str, Any]:
    """Resume el estado acumulado de un equipo antes de la fixture."""
    if home:
        rows = history[history["localId"] == team_id]
        goals_for = rows["golesLocal"]
        goals_against = rows["golesVisitante"]
    else:
        rows = history[history["visitanteId"] == team_id]
        goals_for = rows["golesVisitante"]
        goals_against = rows["golesLocal"]
    points = 0
    outcomes: list[str] = []
    for _, row in rows.sort_values("matchDate").iterrows():
        own, opponent = (
            _num(row["golesLocal"] if home else row["golesVisitante"]),
            _num(row["golesVisitante"] if home else row["golesLocal"]),
        )
        if own > opponent:
            points += 3
            outcomes.append("W")
        elif own == opponent:
            points += 1
            outcomes.append("D")
        else:
            outcomes.append("L")
    recent = outcomes[-5:]
    return {
        "matches": len(rows),
        "points": points,
        "position": 0,
        "goals_for": float(goals_for.sum()) if len(rows) else 0.0,
        "goals_against": float(goals_against.sum()) if len(rows) else 0.0,
        "form_points": sum(3 if x == "W" else 1 if x == "D" else 0 for x in recent),
        "streak": sum(1 if x == "W" else -1 if x == "L" else 0 for x in recent),
        "outcomes": outcomes,
    }


def _history_entries(
    history: pd.DataFrame, team_id: int, *, home: bool | None = None
) -> list[tuple[date | None, float, float, int]]:
    """Devuelve goles a favor/en contra y resultado antes de una fixture."""
    mask = (history["localId"] == team_id) | (history["visitanteId"] == team_id)
    if home is True:
        mask &= history["localId"] == team_id
    elif home is False:
        mask &= history["visitanteId"] == team_id
    entries: list[tuple[date | None, float, float, int]] = []
    for _, row in history.loc[mask].sort_values("matchDate").iterrows():
        is_home = int(row["localId"]) == team_id
        own = _num(row["golesLocal"] if is_home else row["golesVisitante"])
        opponent = _num(row["golesVisitante"] if is_home else row["golesLocal"])
        result = 1 if own > opponent else -1 if own < opponent else 0
        entries.append((pd.Timestamp(row["matchDate"]).date(), own, opponent, result))
    return entries


def _rolling_entries(
    entries: list[tuple[date | None, float, float, int]], size: int
) -> tuple[float, float]:
    recent = entries[-size:]
    if not recent:
        return 0.0, 0.0
    return (
        sum(entry[1] for entry in recent) / len(recent),
        sum(entry[2] for entry in recent) / len(recent),
    )


def _rest_days(entries: list[tuple[date | None, float, float, int]], current: date) -> float:
    if not entries or entries[-1][0] is None:
        return -1.0
    return float(max(0, (current - entries[-1][0]).days))


def _recent_count(entries: list[tuple[date | None, float, float, int]], current: date) -> int:
    return sum(
        1 for entry in entries if entry[0] is not None and 0 < (current - entry[0]).days <= 7
    )


def _streak(entries: list[tuple[date | None, float, float, int]]) -> int:
    return sum(entry[3] for entry in entries[-5:])


def _positions(history: pd.DataFrame) -> dict[int, int]:
    """Calcula posiciones actuales de la competición según puntos y golaverage."""
    table: dict[int, list[float]] = defaultdict(lambda: [0, 0, 0])
    for _, row in history.iterrows():
        home, away = int(row["localId"]), int(row["visitanteId"])
        hg, ag = _num(row["golesLocal"]), _num(row["golesVisitante"])
        table[home][1] += hg - ag
        table[away][1] += ag - hg
        table[home][2] += hg
        table[away][2] += ag
        if hg > ag:
            table[home][0] += 3
        elif hg < ag:
            table[away][0] += 3
        else:
            table[home][0] += 1
            table[away][0] += 1
    ordered = sorted(
        table, key=lambda team: (-table[team][0], -table[team][1], -table[team][2], team)
    )
    return {team: index + 1 for index, team in enumerate(ordered)}


def build_fixture_features(
    historical: pd.DataFrame, fixtures: pd.DataFrame, as_of: date
) -> pd.DataFrame:
    """Genera filas compatibles con ``ML_COLUMNS`` sin usar datos posteriores."""
    history = cutoff_history(historical, as_of)
    rows: list[dict[str, Any]] = []
    for _, fixture in fixtures.iterrows():
        division = int(fixture["division"])
        season = str(fixture["temporada"])
        jornada = int(fixture["jornada"])
        local_id, away_id = int(fixture["localId"]), int(fixture["visitanteId"])
        competition = history[
            (history["division"] == division)
            & (history["temporada"].astype(str) == season)
            & (pd.to_datetime(history["matchDate"]).dt.date < fixture["matchDate"])
        ]
        local = _team_state(competition, local_id, True)
        away = _team_state(competition, away_id, False)
        local_history = _history_entries(competition, local_id)
        away_history = _history_entries(competition, away_id)
        local_home_history = _history_entries(competition, local_id, home=True)
        away_away_history = _history_entries(competition, away_id, home=False)
        fixture_date = fixture["matchDate"]
        local_goals_5 = _rolling_entries(local_history, 5)
        local_goals_10 = _rolling_entries(local_history, 10)
        away_goals_5 = _rolling_entries(away_history, 5)
        away_goals_10 = _rolling_entries(away_history, 10)
        positions = _positions(competition)
        h2h = competition[
            ((competition["localId"] == local_id) & (competition["visitanteId"] == away_id))
            | ((competition["localId"] == away_id) & (competition["visitanteId"] == local_id))
        ]
        local_wins = sum(
            1
            for _, match in h2h.iterrows()
            if (
                int(match["localId"]) == local_id
                and _num(match["golesLocal"]) > _num(match["golesVisitante"])
            )
            or (
                int(match["visitanteId"]) == local_id
                and _num(match["golesVisitante"]) > _num(match["golesLocal"])
            )
        )
        away_wins = (
            len(h2h)
            - local_wins
            - sum(
                1
                for _, match in h2h.iterrows()
                if _num(match["golesLocal"]) == _num(match["golesVisitante"])
            )
        )
        market_local = _num(fixture.get("localMarketValue"), -1.0)
        market_away = _num(fixture.get("visitanteMarketValue"), -1.0)
        row = {column: 0 for column in ML_COLUMNS}
        row.update(
            {
                "division": division,
                "temporada": season,
                "jornada": jornada,
                "localId": local_id,
                "visitanteId": away_id,
                "diferenciaPuntos": local["points"] - away["points"],
                "diferenciaPosicion": positions.get(away_id, 0) - positions.get(local_id, 0),
                "diferenciaGolesNeta": (local["goals_for"] - local["goals_against"])
                - (away["goals_for"] - away["goals_against"]),
                "rachaLocal": local["streak"],
                "rachaVisitante": away["streak"],
                "h2hMatches": len(h2h),
                "h2hBalance": local_wins - away_wins,
                "golesLocal": -1,
                "golesVisitante": -1,
                "distanciaKm": _num(fixture.get("distanciaKm"), -1.0),
                "golesFavor5Local": local_goals_5[0],
                "golesContra5Local": local_goals_5[1],
                "golesFavor10Local": local_goals_10[0],
                "golesContra10Local": local_goals_10[1],
                "golesFavor5Visitante": away_goals_5[0],
                "golesContra5Visitante": away_goals_5[1],
                "golesFavor10Visitante": away_goals_10[0],
                "golesContra10Visitante": away_goals_10[1],
                "rachaLocalCasa": _streak(local_home_history),
                "rachaVisitanteFuera": _streak(away_away_history),
                "partidosCasaLocal": len(local_home_history),
                "partidosFueraVisitante": len(away_away_history),
                "diasDescansoLocal": _rest_days(local_history, fixture_date),
                "diasDescansoVisitante": _rest_days(away_history, fixture_date),
                "partidos7DiasLocal": _recent_count(local_history, fixture_date),
                "partidos7DiasVisitante": _recent_count(away_history, fixture_date),
                "diferenciaDescanso": _rest_days(local_history, fixture_date)
                - _rest_days(away_history, fixture_date),
                "sobreRendimientoLocal": 0.0,
                "sobreRendimientoVisitante": 0.0,
                "diferenciaValorMercado": market_local - market_away
                if market_local >= 0 and market_away >= 0
                else -1.0,
                "ratioValorMercado": market_local / market_away
                if market_local >= 0 and market_away > 0
                else -1.0,
                "resultado1X2": "",
            }
        )
        rows.append({column: row[column] for column in ML_COLUMNS})
    return pd.DataFrame(rows, columns=ML_COLUMNS)
