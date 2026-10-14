"""Contexto aislado por ejecución; evita contaminación entre invocaciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import FootballClasses as fc


@dataclass
class ExecutionContext:
    source: str = "web"
    enable_market: bool = True
    enable_referees: bool = True
    output_path: str = "TestSave.csv"
    input_path: str = "TestSave.csv"
    market_path: str = "market_values.json"
    referees_path: str = "referees.json"
    current_match_id: int = 1
    current_team_id: int = 0
    team_names_to_id: dict[str, int] = field(default_factory=dict)
    ids_to_team: dict[int, fc.Equipo] = field(default_factory=dict)
    all_seasons_info: dict[int, dict[str, Any]] = field(default_factory=dict)
    market_helper: Any = None
    referees_helper: Any = None

    def get_or_create_team(self, name: str) -> int:
        if name in self.team_names_to_id:
            return self.team_names_to_id[name]
        self.current_team_id += 1
        team_id = self.current_team_id
        self.team_names_to_id[name] = team_id
        self.ids_to_team[team_id] = fc.Equipo(team_id, name)
        return team_id

    def next_match_id(self) -> int:
        value = self.current_match_id
        self.current_match_id += 1
        return value

    def add_season(self, division: int, season: str, data: Any) -> None:
        self.all_seasons_info.setdefault(division, {})[season] = data


# Alias español para consumidores nuevos.
ContextoDeEjecucion = ExecutionContext
