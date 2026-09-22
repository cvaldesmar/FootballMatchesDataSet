#Autor original Ricardo Moya https://github.com/RicardoMoya/FootballMatchesDataSet
import copy
from dataclasses import dataclass
from datetime import datetime

class Equipo:
    def __init__(self, idGlobalClub, nombre, valorActual=0):
        self.idGlobalClub = idGlobalClub
        self.nombre = nombre
        self.valorActual = valorActual

    def returnWithCurrentValue(self, valorActual):
        aux = copy.copy(self)
        aux.valorActual = valorActual
        return aux

    def __str__(self):
        val_str = f"{self.valorActual}M€" if self.valorActual > 0 else "N/D"
        return f"{self.idGlobalClub}-{self.nombre} ({val_str})"

    def __repr__(self):
        return self.__str__()


class Partido:

    def __init__(self, idPartido, division, temporada, jornada, matchDate, arbitroName, arbitroId, localName, localId, localMarketValue, puntosLocal, golesafavorlocal, golesencontralocal, visitanteName, visitanteId, visitanteMarketValue, puntosVisitante, golesafavorvisitante, golesencontravisitante, golesLocal, golesVisitante, golDiff):
        self.idPartido = int(idPartido)
        self.division = int(division)
        self.temporada = str(temporada)
        self.jornada = int(jornada)
        self.matchDate = datetime.strptime(matchDate, '%Y-%m-%d').date()
        self.arbitroName = arbitroName
        self.arbitroId = arbitroId
        self.localName = str(localName)
        self.localId = int(localId)
        self.localMarketValue = int(localMarketValue)
        self.puntosLocal = int(puntosLocal)
        self.golesafavorlocal = int(golesafavorlocal)
        self.golesencontralocal = int(golesencontralocal)
        self.visitanteName = str(visitanteName)
        self.visitanteId = int(visitanteId)
        self.visitanteMarketValue = int(visitanteMarketValue)
        self.puntosVisitante = int(puntosVisitante)
        self.golesafavorvisitante = int(golesafavorvisitante)
        self.golesencontravisitante = int(golesencontravisitante)
        self.golesLocal = int(golesLocal)
        self.golesVisitante = int(golesVisitante)
        self.golDiff = int(golDiff)

    def __str__(self):
        return (f"Partido "
                f"{self.idPartido}::{self.division}::{self.temporada}::{self.jornada}::{self.matchDate}::{self.arbitroName}::{self.arbitroId}::"
                f"{self.localId}::{self.localMarketValue}::{self.puntosLocal}::{self.golesafavorlocal}::{self.golesencontralocal}::"
                f"{self.visitanteId}::{self.visitanteMarketValue}::{self.puntosVisitante}::{self.golesafavorvisitante}::{self.golesencontravisitante}::"
                f"{self.golesLocal}::{self.golesVisitante}::{self.golDiff}")

