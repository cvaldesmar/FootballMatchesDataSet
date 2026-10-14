# Autor original Ricardo Moya https://github.com/RicardoMoya/FootballMatchesDataSet
import copy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Self


@dataclass
class Equipo:
    idGlobalClub: int
    nombre: str
    valorActual: int = 0

    def returnWithCurrentValue(self, valorActual: int) -> Self:
        aux = copy.copy(self)
        aux.valorActual = valorActual
        return aux

    def __str__(self) -> str:
        val_str = f"{self.valorActual}M€" if self.valorActual > 0 else "N/D"
        return f"{self.idGlobalClub}-{self.nombre} ({val_str})"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass(kw_only=True)
class Partido:
    idPartido: int
    division: int
    temporada: str
    jornada: int
    matchDate: date
    arbitroName: str
    arbitroId: int
    localName: str
    localId: int
    localMarketValue: int
    puntosLocal: int
    golesafavorlocal: int
    golesencontralocal: int
    visitanteName: str
    visitanteId: int
    visitanteMarketValue: int
    puntosVisitante: int
    golesafavorvisitante: int
    golesencontravisitante: int
    golesLocal: int
    golesVisitante: int
    golDiff: int
    distanciaKm: float = -1.0
    resultado1X2: str = ""
    posicionLocal: int = 0
    posicionVisitante: int = 0
    diferenciaPuntos: int = 0
    rachaLocal: int = 0
    rachaVisitante: int = 0
    formaLocal: str = ""
    formaVisitante: str = ""
    h2hLocalWins: int = 0
    h2hDraws: int = 0
    h2hAwayWins: int = 0
    h2hMatches: int = 0
    campeonId: int = -1
    descensoConfirmadoLocal: int = 0
    descensoConfirmadoVisitante: int = 0
    presionLocal: int = 0
    presionVisitante: int = 0
    rivalidad: int = 0

    def __post_init__(self) -> None:
        self.idPartido = int(self.idPartido)
        self.division = int(self.division)
        self.temporada = str(self.temporada)
        self.jornada = int(self.jornada)
        if isinstance(self.matchDate, str):
            self.matchDate = datetime.strptime(self.matchDate, "%Y-%m-%d").date()
        self.arbitroId = int(self.arbitroId)
        self.localName = str(self.localName)
        self.localId = int(self.localId)
        self.localMarketValue = int(self.localMarketValue)
        self.puntosLocal = int(self.puntosLocal)
        self.golesafavorlocal = int(self.golesafavorlocal)
        self.golesencontralocal = int(self.golesencontralocal)
        self.visitanteName = str(self.visitanteName)
        self.visitanteId = int(self.visitanteId)
        self.visitanteMarketValue = int(self.visitanteMarketValue)
        self.puntosVisitante = int(self.puntosVisitante)
        self.golesafavorvisitante = int(self.golesafavorvisitante)
        self.golesencontravisitante = int(self.golesencontravisitante)
        self.golesLocal = int(self.golesLocal)
        self.golesVisitante = int(self.golesVisitante)
        self.golDiff = int(self.golDiff)
        self.distanciaKm = float(self.distanciaKm)
        self.resultado1X2 = (
            "1"
            if self.golesLocal > self.golesVisitante
            else "X"
            if self.golesLocal == self.golesVisitante
            else "2"
        )
        self.posicionLocal = int(self.posicionLocal)
        self.posicionVisitante = int(self.posicionVisitante)
        self.diferenciaPuntos = int(self.diferenciaPuntos)
        self.rachaLocal = int(self.rachaLocal)
        self.rachaVisitante = int(self.rachaVisitante)
        self.formaLocal = str(self.formaLocal)
        self.formaVisitante = str(self.formaVisitante)
        self.h2hLocalWins = int(self.h2hLocalWins)
        self.h2hDraws = int(self.h2hDraws)
        self.h2hAwayWins = int(self.h2hAwayWins)
        self.h2hMatches = int(self.h2hMatches)
        self.campeonId = int(self.campeonId)
        self.descensoConfirmadoLocal = int(self.descensoConfirmadoLocal)
        self.descensoConfirmadoVisitante = int(self.descensoConfirmadoVisitante)
        self.presionLocal = int(self.presionLocal)
        self.presionVisitante = int(self.presionVisitante)
        self.rivalidad = int(self.rivalidad)

    def __str__(self) -> str:
        return (
            f"Partido "
            f"{self.idPartido}::{self.division}::{self.temporada}::{self.jornada}::{self.matchDate}::{self.arbitroName}::{self.arbitroId}::"
            f"{self.localId}::{self.localMarketValue}::{self.puntosLocal}::{self.golesafavorlocal}::{self.golesencontralocal}::"
            f"{self.visitanteId}::{self.visitanteMarketValue}::{self.puntosVisitante}::{self.golesafavorvisitante}::{self.golesencontravisitante}::"
            f"{self.golesLocal}::{self.golesVisitante}::{self.golDiff}::{self.distanciaKm}::{self.posicionLocal}::{self.posicionVisitante}::{self.diferenciaPuntos}::"
            f"{self.rachaLocal}::{self.rachaVisitante}::{self.formaLocal}::{self.formaVisitante}::"
            f"{self.h2hLocalWins}::{self.h2hDraws}::{self.h2hAwayWins}::{self.h2hMatches}::"
            f"{self.campeonId}::{self.descensoConfirmadoLocal}::{self.descensoConfirmadoVisitante}::"
            f"{self.presionLocal}::{self.presionVisitante}::{self.rivalidad}"
        )
