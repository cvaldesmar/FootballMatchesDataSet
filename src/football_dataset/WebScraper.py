"""Adaptador web de BDFutbol: HTTP, parseo y registro de equipos."""

from __future__ import annotations

from . import Const as const
from . import UtilsAndGlobals as ut
from .context import ExecutionContext
from .http_client import HttpClient
from .parsers import BDFutbolParser


class WebScraper:
    def __init__(
        self,
        division: int,
        temporada: str,
        context: ExecutionContext | None = None,
        http_client: HttpClient | None = None,
        parser: BDFutbolParser | None = None,
    ):
        self.context = context or ExecutionContext()
        self.http_client = http_client or HttpClient()
        self.parser = parser or BDFutbolParser()
        self.division = division
        self.temporada = temporada
        self.data = self.filterData(division, temporada)
        self.teamsSeasonIdToGlobalIdDict = self.getTeamsSeasonIdToGlobalIdDict()
        self.matchesArray = self.getMatchesArray()

    def filterData(self, division: int, temporada: str) -> str:
        division_string = "" if division == 1 else "2a"
        url = const.SEASON_URL % (temporada, division_string)
        response = self.http_client.get(url)
        return response.text

    def getTeamsSeasonIdToGlobalIdDict(self) -> dict[int, int]:
        teams, _ = self.parser.parse(self.data)
        result = {}
        for team in teams:
            name = ut.GET_NORMALIZED_TEAM_NAME(team.name)
            result[team.season_id] = self.context.get_or_create_team(name)
        return result

    def getMatchesArray(self) -> list[list[object]]:
        _, matches = self.parser.parse(self.data)
        result = []
        for match in matches:
            try:
                home_id = self.teamsSeasonIdToGlobalIdDict[match.home_season_id]
                away_id = self.teamsSeasonIdToGlobalIdDict[match.away_season_id]
            except KeyError as error:
                raise ValueError(
                    f"Partido referencia equipo de temporada desconocido: {error}"
                ) from error
            home_name = self.context.ids_to_team[home_id].nombre
            away_name = self.context.ids_to_team[away_id].nombre
            result.append(
                [
                    match.jornada,
                    match.match_date.isoformat(),
                    home_id,
                    home_name,
                    away_id,
                    away_name,
                    match.home_goals,
                    match.away_goals,
                    match.home_goals - match.away_goals,
                ]
            )
        return result
