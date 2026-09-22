import UtilsAndGlobals as ut
import csv

class FileScraper:
    def __init__(self, division, temporada):
        self.data = self.filterData(division, temporada)
        self.teamsSeasonIdToGlobalIdDict = self.getTeamsSeasonIdToGlobalIdDict()
        self.matchesArray = self.getMatchesArray()

    def filterData(self, division, temporada):
        filteredRows = []
        input_path = getattr(ut, 'INPUT_SEASONS_PATH', ut.SAVE_SEASONS_PATH)
        with open(input_path, 'r', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                rowDivision = int(row['division'])
                rowSeason = row['temporada']
                if rowDivision == division and rowSeason == temporada:
                    filteredRows.append(row)
        return filteredRows

    def getTeamsSeasonIdToGlobalIdDict(self):
        seasonIdToGlobalId = {}
        teamsNames = list({(d['localName'], d["localId"]) for d in self.data})
        for team in teamsNames:
            seasonTeamId = int(team[1])
            teamName = ut.GET_NORMALIZED_TEAM_NAME(team[0])
            globalTeamId = ut.GET_GLOBAL_EQUIPO_ID(teamName)
            seasonIdToGlobalId[seasonTeamId] = globalTeamId
        return seasonIdToGlobalId


    def getMatchesArray(self):
        matchesArray = []
        for match in self.data:
            jornada = int(match["jornada"])
            matchDate = match["matchDate"]
            localGlobalId = self.teamsSeasonIdToGlobalIdDict[int(match["localId"])]
            localName = match["localName"]
            visitanteGlobalId = self.teamsSeasonIdToGlobalIdDict[int(match["visitanteId"])]
            visitanteName = match["visitanteName"]
            golesLocal = int(match["golesLocal"])
            golesVisitante = int(match["golesVisitante"])
            golDiff = int(match["golDiff"])
            matchesArray.append([jornada, matchDate, localGlobalId, localName, visitanteGlobalId, visitanteName, golesLocal, golesVisitante,golDiff])
        return matchesArray

