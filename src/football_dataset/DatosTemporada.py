from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, cast

from . import Const as const
from . import FootballClasses as fc
from . import UtilsAndGlobals as ut
from .context import ExecutionContext
from .FileScraper import FileScraper
from .MarketHelper import MarketHelper
from .RefereesHelper import RefereesHelper
from .WebScraper import WebScraper

logger = logging.getLogger(__name__)


class DatosTemporada:
    def __init__(
        self,
        division: int,
        temporada: str,
        context: ExecutionContext | None = None,
        season_loader: Any = None,
        market_helper: Any = None,
        referees_helper: Any = None,
    ):
        self.context = context or ExecutionContext()
        self.division = division
        self.temporada = temporada
        self.market_helper = market_helper or MarketHelper(self.context)
        self.referees_helper = referees_helper or RefereesHelper(self.context)
        self.seasonLoader = season_loader or (
            FileScraper(division, temporada, self.context)
            if self.context.source == "file"
            else WebScraper(division, temporada, self.context)
        )
        self.temporadaAñoStart = int(temporada.split("-")[0])
        self.puntosPorVictoria = 3 if self.temporadaAñoStart > 1994 else 2
        self.clasificacion: dict[int, int] = {}
        self.golesafavor: dict[int, int] = {}
        self.golesencontra: dict[int, int] = {}
        self.jornadas: dict[int, dict[int, fc.Partido]] = {}
        self._frozen_standings: dict[int, dict[int, tuple[int, int, int, int]]] = {}
        self._team_history: dict[int, list[tuple[str, int]]] = defaultdict(list)
        self._h2h_history: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
        self._frozen_form: dict[int, dict[int, tuple[int, str]]] = {}
        self._frozen_h2h: dict[int, dict[tuple[int, int], tuple[int, int, int, int]]] = {}
        self._frozen_competitive: dict[int, dict[str, Any]] = {}
        self._batch_update = False
        self.loadEquipos()
        self.loadMatches()

    def loadEquipos(self) -> None:
        ut.RAISE_IF(not self.seasonLoader.teamsSeasonIdToGlobalIdDict, "NO HAY EQUIPOS QUE CARGAR")
        self.numJornadas = 2 * (len(self.seasonLoader.teamsSeasonIdToGlobalIdDict) - 1)
        for equipo_id in set(self.seasonLoader.teamsSeasonIdToGlobalIdDict.values()):
            self.clasificacion[equipo_id] = 0
            self.golesafavor[equipo_id] = 0
            self.golesencontra[equipo_id] = 0

    def loadMatches(self) -> None:
        ut.RAISE_IF(not self.seasonLoader.matchesArray, "NO HAY PARTIDOS QUE CARGAR")
        grouped_matches: dict[int, list[list[Any]]] = {}
        for raw_match in self.seasonLoader.matchesArray:
            match = cast(list[Any], raw_match)
            grouped_matches.setdefault(int(match[0]), []).append(match)

        self._batch_update = True
        try:
            for jornada in sorted(grouped_matches):
                self._frozen_standings[jornada] = self._freeze_standings()
                self._frozen_form[jornada] = self._freeze_form()
                self._frozen_h2h[jornada] = self._freeze_h2h()
                self._frozen_competitive[jornada] = self._compute_competitive_context(
                    jornada, self._frozen_standings[jornada]
                )
                for match in grouped_matches[jornada]:
                    self.addMatch(self.division, *match)
                for match in grouped_matches[jornada]:
                    _, _, home_id, _, away_id, _, home_goals, away_goals, _ = match
                    self.updateClassification(home_goals, away_goals, home_id, away_id)
                    self._record_history(home_id, away_id, home_goals, away_goals)
        finally:
            self._batch_update = False

    def _freeze_standings(self) -> dict[int, tuple[int, int, int, int]]:
        """Devuelve posición, puntos y estadísticas al inicio de una jornada."""
        ordered = sorted(
            self.clasificacion,
            key=lambda team_id: (
                -self.clasificacion[team_id],
                -(self.golesafavor[team_id] - self.golesencontra[team_id]),
                -self.golesafavor[team_id],
                team_id,
            ),
        )
        return {
            team_id: (
                position,
                self.clasificacion[team_id],
                self.golesafavor[team_id],
                self.golesencontra[team_id],
            )
            for position, team_id in enumerate(ordered, start=1)
        }

    def addMatch(
        self,
        division: int,
        jornada: int,
        matchDate: Any,
        localGlobalId: int,
        localName: str,
        visitanteGlobalId: int,
        visitanteName: str,
        golesLocal: int,
        golesVisitante: int,
        golDiff: int,
    ) -> None:
        localName = self.context.ids_to_team[localGlobalId].nombre
        visitanteName = self.context.ids_to_team[visitanteGlobalId].nombre
        if self._batch_update:
            standings = self._frozen_standings[int(jornada)]
            form = self._frozen_form[int(jornada)]
            h2h = self._frozen_h2h[int(jornada)]
            competitive = self._frozen_competitive[int(jornada)]
        else:
            standings = self._freeze_standings()
            form = self._freeze_form()
            h2h = self._freeze_h2h()
            competitive = self._compute_competitive_context(int(jornada), standings)
        local_position, local_points, local_goals_for, local_goals_against = standings[
            localGlobalId
        ]
        away_position, away_points, away_goals_for, away_goals_against = standings[
            visitanteGlobalId
        ]
        local_streak, local_form = form[localGlobalId]
        away_streak, away_form = form[visitanteGlobalId]
        h2h_local_wins, h2h_draws, h2h_away_wins, h2h_matches = h2h[
            (localGlobalId, visitanteGlobalId)
        ]
        campeon_id = competitive["campeon_id"]
        local_competitive = competitive["teams"][localGlobalId]
        away_competitive = competitive["teams"][visitanteGlobalId]
        rivalidad = int(frozenset((localName, visitanteName)) in const.RIVALRIES)
        distancia_km = ut.get_travel_distance_km(localName, visitanteName)
        local_market, away_market = self.market_helper.getTeamsMarketValue(
            division, matchDate, localName, visitanteName
        )
        local_market = float(local_market)
        away_market = float(away_market)
        if local_market > 0:
            self.context.ids_to_team[localGlobalId].valorActual = int(local_market)
        if away_market > 0:
            self.context.ids_to_team[visitanteGlobalId].valorActual = int(away_market)

        referee_name, referee_id, referee_result = self.referees_helper.getMatchRefereeAndResults(
            self.temporadaAñoStart, division, matchDate, localName, visitanteName
        )
        if referee_id not in (None, -1) and referee_result:
            try:
                ref_home, ref_away = (int(value) for value in referee_result.split(":", 1))
                if (ref_home, ref_away) != (int(golesLocal), int(golesVisitante)):
                    logger.warning(
                        "Árbitro %s descartado: resultado incompatible en %s vs %s",
                        referee_name,
                        localName,
                        visitanteName,
                    )
                    referee_name, referee_id = "", -1
            except (TypeError, ValueError):
                referee_name, referee_id = "", -1

        match_id = self.context.next_match_id()
        self.jornadas.setdefault(int(jornada), {})[match_id] = fc.Partido(
            idPartido=match_id,
            division=division,
            temporada=self.temporada,
            jornada=jornada,
            matchDate=matchDate,
            arbitroName=referee_name,
            arbitroId=referee_id,
            localName=localName,
            localId=localGlobalId,
            localMarketValue=int(local_market),
            puntosLocal=local_points,
            golesafavorlocal=local_goals_for,
            golesencontralocal=local_goals_against,
            visitanteName=visitanteName,
            visitanteId=visitanteGlobalId,
            visitanteMarketValue=int(away_market),
            puntosVisitante=away_points,
            golesafavorvisitante=away_goals_for,
            golesencontravisitante=away_goals_against,
            golesLocal=golesLocal,
            golesVisitante=golesVisitante,
            golDiff=golDiff,
            distanciaKm=distancia_km,
            posicionLocal=local_position,
            posicionVisitante=away_position,
            diferenciaPuntos=local_points - away_points,
            rachaLocal=local_streak,
            rachaVisitante=away_streak,
            formaLocal=local_form,
            formaVisitante=away_form,
            h2hLocalWins=h2h_local_wins,
            h2hDraws=h2h_draws,
            h2hAwayWins=h2h_away_wins,
            h2hMatches=h2h_matches,
            campeonId=campeon_id,
            descensoConfirmadoLocal=local_competitive["descenso"],
            descensoConfirmadoVisitante=away_competitive["descenso"],
            presionLocal=local_competitive["presion"],
            presionVisitante=away_competitive["presion"],
            rivalidad=rivalidad,
        )
        if not self._batch_update:
            self.updateClassification(golesLocal, golesVisitante, localGlobalId, visitanteGlobalId)
            self._record_history(localGlobalId, visitanteGlobalId, golesLocal, golesVisitante)

    def _freeze_form(self) -> dict[int, tuple[int, str]]:
        return {
            team_id: (
                sum(points for _, points in history[-5:]),
                "".join(result for result, _ in history[-5:]),
            )
            for team_id, history in self._team_history.items()
        } | {
            team_id: (0, "") for team_id in self.clasificacion if team_id not in self._team_history
        }

    @staticmethod
    def _h2h_key(home_id: int, away_id: int) -> tuple[int, int]:
        ordered = sorted((home_id, away_id))
        return ordered[0], ordered[1]

    def _freeze_h2h(self) -> dict[tuple[int, int], tuple[int, int, int, int]]:
        """Calcula el H2H desde cada posible orientación local/visitante."""
        snapshot = {}
        for local_id in self.clasificacion:
            for away_id in self.clasificacion:
                if local_id == away_id:
                    continue
                key = self._h2h_key(local_id, away_id)
                local_wins = draws = away_wins = 0
                for recorded_home, _recorded_away, outcome in self._h2h_history.get(key, ())[-5:]:
                    perspective = outcome if recorded_home == local_id else -outcome
                    if perspective > 0:
                        local_wins += 1
                    elif perspective < 0:
                        away_wins += 1
                    else:
                        draws += 1
                snapshot[(local_id, away_id)] = (
                    local_wins,
                    draws,
                    away_wins,
                    local_wins + draws + away_wins,
                )
        return snapshot

    def _record_history(self, home_id: int, away_id: int, home_goals: int, away_goals: int) -> None:
        if home_goals > away_goals:
            home_result, away_result = "W", "L"
            outcome = 1
        elif home_goals < away_goals:
            home_result, away_result = "L", "W"
            outcome = -1
        else:
            home_result = away_result = "D"
            outcome = 0
        home_points = self.puntosPorVictoria if outcome > 0 else 1 if outcome == 0 else 0
        away_points = self.puntosPorVictoria if outcome < 0 else 1 if outcome == 0 else 0
        self._team_history[home_id].append((home_result, home_points))
        self._team_history[away_id].append((away_result, away_points))
        self._h2h_history[self._h2h_key(home_id, away_id)].append((home_id, away_id, outcome))

    def _compute_competitive_context(
        self,
        jornada: int,
        standings: dict[int, tuple[int, int, int, int]],
    ) -> dict[str, Any]:
        """Calcula campeón, descenso y presión usando sólo el snapshot previo."""
        if not standings:
            return {"campeon_id": -1, "teams": {}}

        descent_places = const.DESCENSOS_POR_DIVISION.get(self.division, 3)
        last_safe_position = max(1, len(standings) - descent_places)
        remaining = max(0, self.numJornadas - int(jornada) + 1)
        max_gain = remaining * self.puntosPorVictoria
        leader_id = next(team_id for team_id, data in standings.items() if data[0] == 1)
        leader_points = standings[leader_id][1]
        safe_id = next(
            team_id for team_id, data in standings.items() if data[0] == last_safe_position
        )
        safe_points = standings[safe_id][1]

        rivals_can_catch = any(
            team_id != leader_id and points + max_gain >= leader_points
            for team_id, (_, points, _, _) in standings.items()
        )
        champion_id = leader_id if not rivals_can_catch else -1
        teams: dict[int, dict[str, int]] = {}
        for team_id, (position, points, _, _) in standings.items():
            gap_to_leader = leader_points - points
            gap_to_safe = safe_points - points
            mathematically_down = position > last_safe_position and points + max_gain < safe_points

            title_pressure = 0
            if champion_id == -1 and points + max_gain >= leader_points:
                title_pressure = (
                    3 if remaining <= 4 and gap_to_leader <= 2 * self.puntosPorVictoria else 2
                )
                if gap_to_leader > 2 * self.puntosPorVictoria:
                    title_pressure = 1

            relegation_pressure = 0
            if mathematically_down:
                relegation_pressure = 0
            elif position > last_safe_position:
                relegation_pressure = 3 if remaining <= 4 else 2
            elif gap_to_safe > 0 and gap_to_safe <= 2 * self.puntosPorVictoria:
                relegation_pressure = 2 if remaining <= 4 else 1

            teams[team_id] = {
                "descenso": int(mathematically_down),
                "presion": max(title_pressure, relegation_pressure),
            }
        return {"campeon_id": champion_id, "teams": teams}

    def updateClassification(
        self,
        golesLocal: int,
        golesVisitante: int,
        localGlobalId: int,
        visitanteGlobalId: int,
    ) -> None:
        if golesLocal > golesVisitante:
            local_points, away_points = self.puntosPorVictoria, 0
        elif golesLocal < golesVisitante:
            local_points, away_points = 0, self.puntosPorVictoria
        else:
            local_points = away_points = 1
        self.clasificacion[localGlobalId] += local_points
        self.clasificacion[visitanteGlobalId] += away_points
        self.golesafavor[localGlobalId] += golesLocal
        self.golesafavor[visitanteGlobalId] += golesVisitante
        self.golesencontra[localGlobalId] += golesVisitante
        self.golesencontra[visitanteGlobalId] += golesLocal
        self.clasificacion = dict(
            sorted(self.clasificacion.items(), key=lambda item: item[1], reverse=True)
        )

    def printSeasonResults(self) -> None:
        for team_id, points in list(self.clasificacion.items())[:3]:
            print(self.context.ids_to_team[team_id], points)
        print({self.context.ids_to_team[key]: value for key, value in self.clasificacion.items()})

    def printSeasonWinner(self) -> None:
        if not self.clasificacion:
            return
        max_points = max(self.clasificacion.values())
        winners = [
            team_id for team_id, points in self.clasificacion.items() if points == max_points
        ]
        if len(winners) > 1:
            preferred = const.TIED_SEASON_WINNERS.get(self.division, {}).get(self.temporada)
            preferred_id = (
                self.context.team_names_to_id.get(preferred) if preferred is not None else None
            )
            if preferred_id in winners:
                print("EMPATE: GANADOR->", self.context.ids_to_team[preferred_id])
            else:
                names = ", ".join(str(self.context.ids_to_team[team_id]) for team_id in winners)
                print(f"EMPATE EN PRIMER PUESTO ({max_points} pts): {names}")
        else:
            print(f" GANADOR TEMPORADA: {self.context.ids_to_team[winners[0]]}")
