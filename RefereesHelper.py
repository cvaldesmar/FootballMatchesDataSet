import requests, os, pickle
from datetime import datetime
from bs4 import BeautifulSoup
from colorama import Fore, Back, Style
import UtilsAndGlobals as ut


class RefereesHelper:

    _instance = None  # Class variable to store the single instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RefereesHelper, cls).__new__(cls)
            cls._instance._init_singleton()
        return cls._instance

    def _init_singleton(self):
        self.SEASON_DIVISION_MATCHES_REFEREES = {}
        self.REFEREE_NAMES_TO_ID = {}
        self.CURRENT_REFEREE_ID = 1
        if ut.loadReferees:
            self._LOAD_REFEREES_VALUES()

    def getMatchRefereeAndResults(self, temporada, division, matchDate, localName, visitanteName):
        if not ut.loadReferees:
            return ("", -1, "")
        ut.CHECK_KEY_EXISTANCE(temporada, self.SEASON_DIVISION_MATCHES_REFEREES, {})
        ut.CHECK_KEY_EXISTANCE(division, self.SEASON_DIVISION_MATCHES_REFEREES[temporada], lambda: self._scrapeSeasonRefereesMatchesByLeague(temporada, division))
        
        matchKey = f"{matchDate}-{localName}-{visitanteName}"
        if matchKey in self.SEASON_DIVISION_MATCHES_REFEREES[temporada][division]:
            return self.SEASON_DIVISION_MATCHES_REFEREES[temporada][division][matchKey]
        
        return ("", -1, "")

    def _CHECK_REFEREE_ID(self, refereeName):
        if refereeName in self.REFEREE_NAMES_TO_ID:
            return self.REFEREE_NAMES_TO_ID[refereeName]
        self.REFEREE_NAMES_TO_ID[refereeName] = self.CURRENT_REFEREE_ID
        self.CURRENT_REFEREE_ID = self.CURRENT_REFEREE_ID + 1
        return self.CURRENT_REFEREE_ID
        
    def _scrapeSeasonRefereesMatchesByLeague(self, añoTemporada, division):
        refereesNamesIDsAndHrefs=[]
        url  = ut.REFEREES_URL % (division, añoTemporada)
        print(Fore.RED + f"Scraping {añoTemporada}ª Referees"+Fore.RESET + f" {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            th_element =  soup.find('th', string='Árbitros')
            if th_element:
                table_element = th_element.find_parent('table', class_='items')
                elements = table_element.select('.hauptlink:not(.zentriert)')
                for element in elements:
                    a_element = element.find('a')
                    if a_element:
                        arbitroName = a_element.text
                        arbitroHref = a_element['href']
                        arbitroId = self._CHECK_REFEREE_ID(arbitroName)
                        refereesNamesIDsAndHrefs.append([arbitroName, arbitroHref, arbitroId])

        datosPartidosyArbitros = {}
        for referee in refereesNamesIDsAndHrefs:
            refereeName = referee[0]
            refereeHref = referee[1]
            refereeId = referee[2]
            datosArbitro = self._scrapeRefereeMatches(refereeName, refereeHref, refereeId, añoTemporada, division)
            datosPartidosyArbitros.update(datosArbitro)
        return datosPartidosyArbitros

    def _scrapeRefereeMatches(self, arbitroName, arbitroHref, arbitroId, añoTemporada, division):
        partidosDivision = {}
        url = ut.REFEREES_MATCHES_URL % (arbitroHref, añoTemporada, division)
        print(f"Scraping arbitro: {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            laLigaHeadElement =  soup.find('div', class_='content-box-headline--logo')
            if laLigaHeadElement is not None:
                table = laLigaHeadElement.find_next_sibling()
                trs =  table.find_all('tr')
                trs = trs[2:]
                for tr in trs:
                    tds = tr.find_all('td')
                    if len(tds) < 7:
                        continue
                    raw_date = tds[1].get_text(strip=True)
                    if not raw_date:
                        continue
                    try:
                        matchDate = datetime.strptime(raw_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                    except Exception:
                        continue

                    tdsEquipos = tr.find_all('td', class_="no-border-links")
                    if len(tdsEquipos) < 2 or not tdsEquipos[0].find('a') or not tdsEquipos[1].find('a'):
                        continue
                    equipoName1 = tdsEquipos[0].find('a').text.strip()
                    equipoName2 = tdsEquipos[1].find('a').text.strip()
                    equipoName1alternative = tdsEquipos[0].find('a').get('title', None)
                    equipoName2alternative = tdsEquipos[1].find('a').get('title', None)
                    
                    res_tag = tdsEquipos[1].find_next_sibling().find('a', class_='ergebnis-link')
                    resultado = res_tag.text.strip() if res_tag else ""

                    equipo1ID = ut.GET_GLOBAL_EQUIPO_ID_FROM_TRANSFERMARKT_NAME(equipoName1, equipoName1alternative)
                    equipo2ID = ut.GET_GLOBAL_EQUIPO_ID_FROM_TRANSFERMARKT_NAME(equipoName2, equipoName2alternative)
                    if equipo1ID is not None and equipo2ID is not None:
                        team1_name = ut.IDs_TO_TEAM[equipo1ID].nombre if equipo1ID in ut.IDs_TO_TEAM else None
                        team2_name = ut.IDs_TO_TEAM[equipo2ID].nombre if equipo2ID in ut.IDs_TO_TEAM else None
                        if team1_name and team2_name:
                            matchKey = f"{matchDate}-{team1_name}-{team2_name}"
                            partidosDivision[matchKey] = [arbitroName, arbitroId, resultado]
        return partidosDivision

    def SAVE_REFEREES_VALUES(self, path=None):
        path = path or ut.SAVE_REFEREES_PATH
        with open(path, 'wb') as file:
            pickle.dump(self.SEASON_DIVISION_MATCHES_REFEREES, file)

    def _LOAD_REFEREES_VALUES(self, path=None):
        path = path or ut.SAVE_REFEREES_PATH
        if os.path.exists(path):
            with open(path, 'rb') as file:
                loaded_dict = pickle.load(file)
            self.SEASON_DIVISION_MATCHES_REFEREES = loaded_dict