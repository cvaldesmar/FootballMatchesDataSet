"""Modelos inmutables intercambiados por los parsers."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RawTeam:
    season_id: int
    name: str


@dataclass(frozen=True)
class RawMatch:
    jornada: int
    match_date: date
    home_season_id: int
    away_season_id: int
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class MarketValue:
    team_name: str
    value: float


@dataclass(frozen=True)
class RefereeMatch:
    date: str
    home_name: str
    away_name: str
    referee_name: str
    referee_id: int
    result: str
