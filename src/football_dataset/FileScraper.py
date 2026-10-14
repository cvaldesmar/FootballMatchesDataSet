"""Adaptador CSV: valida y transforma filas mediante un parser independiente."""

from __future__ import annotations

from . import UtilsAndGlobals as ut
from .context import ExecutionContext
from .parsers import BDFutbolCSVParser


class FileScraper:
    def __init__(
        self,
        division: int,
        temporada: str,
        context: ExecutionContext | None = None,
        parser: BDFutbolCSVParser | None = None,
    ):
        self.context = context or ExecutionContext(source="file")
        self.parser = parser or BDFutbolCSVParser()
        self.division = division
        self.temporada = temporada
        self.data = self.filterData(division, temporada)
        self.teamsSeasonIdToGlobalIdDict = self.getTeamsSeasonIdToGlobalIdDict()
        self.matchesArray = self.getMatchesArray()

    def filterData(self, division: int, temporada: str) -> list[dict[str, str]]:
        input_path = self.context.input_path
        return self.parser.parse(input_path, division, temporada)

    def getTeamsSeasonIdToGlobalIdDict(self) -> dict[int, int]:
        result = {}
        for row in self.data:
            season_id = int(row["localId"])
            name = ut.GET_NORMALIZED_TEAM_NAME(row["localName"])
            result[season_id] = self.context.get_or_create_team(name)
            away_season_id = int(row["visitanteId"])
            away_name = ut.GET_NORMALIZED_TEAM_NAME(row["visitanteName"])
            result[away_season_id] = self.context.get_or_create_team(away_name)
        return result

    def getMatchesArray(self) -> list[list[object]]:
        result = []
        for row in self.data:
            home_id = self.teamsSeasonIdToGlobalIdDict[int(row["localId"])]
            away_id = self.teamsSeasonIdToGlobalIdDict[int(row["visitanteId"])]
            result.append(
                [
                    int(row["jornada"]),
                    row["matchDate"],
                    home_id,
                    self.context.ids_to_team[home_id].nombre,
                    away_id,
                    self.context.ids_to_team[away_id].nombre,
                    int(row["golesLocal"]),
                    int(row["golesVisitante"]),
                    int(row["golDiff"]),
                ]
            )
        return result
