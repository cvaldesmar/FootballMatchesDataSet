import requests, json, os, pickle
from bs4 import BeautifulSoup
from colorama import Fore, Back, Style
import UtilsAndGlobals as ut
from datetime import datetime, timedelta

class MarketHelper:
    _instance = None  # Class variable to store the single instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MarketHelper, cls).__new__(cls)
            cls._instance._init_singleton()
        return cls._instance

    def _init_singleton(self):
        self.firstMarketDate = datetime.now().date()
        self.MARKET_INFO = {}
        if ut.loadMarket:
            self._LOAD_MARKET_VALUES()

    def _ensureDivisionMarketDates(self, division):
        if not ut.loadMarket:
            return
        if division not in self.MARKET_INFO or not self.MARKET_INFO[division]:
            self.MARKET_INFO[division] = self._scrapeMarketDatesToDictionary(division)

    def _scrapeMarketDatesToDictionary(self, division):
        print(Fore.RED + f"Scraping {division}ª Market Dates"+Fore.RESET)
        url = ut.MARKET_URL % (division,"")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            select_element = soup.find('select', {'class': 'chzn-select'})
            if select_element:
                option_values = {datetime.strptime(option['value'], "%Y-%m-%d").date(): {} for option in select_element.find_all('option')}
                self._SET_FIRST_MARKET_DATE(option_values)
                return option_values
        ut.RAISE("No scraping Market Dates Found")

    def scrapeMarketTeamValues(self, division, realMarketDate):
        print(Fore.MAGENTA + f"Scraping {division}ª Market Values ON {realMarketDate}"+Fore.RESET)
        teamsValues = {}
        marketUrl = ut.MARKET_URL % (division, realMarketDate.strftime("%Y-%m-%d"))
        req = requests.get(marketUrl, headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.9999.999 Safari/537.36'})
        localMarketNodes = BeautifulSoup(req.text, "html.parser").find_all('td', {'class': 'hauptlink no-border-links'})
        for localNode in localMarketNodes:
            teamName = localNode.find("a")['title']
            teamValueText = localNode.find_next_siblings()[1].find("a").string
            teamsValues[teamName] = -1 if teamValueText == "-" else float(teamValueText.split(" ")[0].replace(",", ".")) * 1000 if "mil mill." in teamValueText else float(teamValueText.split(" ")[0].replace(",", "."))
        return teamsValues

    def getTeamsMarketValue(self, division, matchDate, localName, visitanteName):
        if not ut.loadMarket:
            return (-1, -1)
        return [self._getMarketValue(division, localName, matchDate), self._getMarketValue(division, visitanteName, matchDate)]

    def _getMarketValue(self, division, equipoName, matchDate):
        if not ut.loadMarket:
            return -1

        self._ensureDivisionMarketDates(division)
        if division not in self.MARKET_INFO or not self.MARKET_INFO[division]:
            return -1

        matchDateObj = datetime.strptime(matchDate, '%Y-%m-%d').date() if isinstance(matchDate, str) else matchDate
        if matchDateObj < self.firstMarketDate:
            return -1

        # Obtener candidatos para el nombre del equipo según mapeos conocidos
        tm_names = ut.NAMES_TO_TRANSFERMARKT_NAMES.get(equipoName, equipoName)
        candidate_names = tm_names if isinstance(tm_names, list) else [tm_names]
        if equipoName not in candidate_names:
            candidate_names.append(equipoName)

        # Buscar en la división actual y fallback en la división alternativa
        backupDivision = 1 if division == 2 else 2
        self._ensureDivisionMarketDates(backupDivision)

        for div in (division, backupDivision):
            if div not in self.MARKET_INFO or not self.MARKET_INFO[div]:
                continue

            # Buscar fecha de mercado más cercana (anterior o igual al partido)
            past_dates = [d for d in self.MARKET_INFO[div] if (matchDateObj - d).days >= 0]
            divMarketDate = min(past_dates, key=lambda d: (matchDateObj - d).days) if past_dates else min(self.MARKET_INFO[div], key=lambda d: abs((d - matchDateObj).days))
            if not divMarketDate:
                continue

            if not self.MARKET_INFO[div].get(divMarketDate):
                self.MARKET_INFO[div][divMarketDate] = self.scrapeMarketTeamValues(div, divMarketDate)

            market_dict = self.MARKET_INFO[div][divMarketDate]
            if not market_dict:
                continue

            # 1. Coincidencia exacta de alguno de los nombres candidatos
            for name in candidate_names:
                if name in market_dict:
                    return market_dict[name]

            # 2. Coincidencia por contención de substring (ej. 'Espanyol' en 'RCD Espanyol')
            for name in candidate_names:
                for key, val in market_dict.items():
                    if name in key or key in name:
                        return val

            # 3. Coincidencia por texto normalizado (sin tildes, acrónimos FC/CF/UD, etc.)
            for name in candidate_names:
                clean_name = ut._clean_team_text(name)
                for key, val in market_dict.items():
                    if clean_name == ut._clean_team_text(key):
                        return val

        return -1

    def _SET_FIRST_MARKET_DATE(self, collection):
        earliest_date = min(collection)
        if earliest_date < self.firstMarketDate:
            self.firstMarketDate = earliest_date

    def SAVE_MARKET_VALUES(self, path=None):
        path = path or ut.SAVE_MARKET_PATH
        with open(path, 'wb') as file:
            pickle.dump(self.MARKET_INFO, file)
        # with open('uncorrectedMarketNames.txt', 'w', encoding='utf-8') as f:
        #     f.write(f"{self.notInCorrectionTeams}")
        # with open('notInMarketNames.txt', 'w', encoding='utf-8') as f:
        #     f.write(f"{self.notInMarketTeams}")

    def _LOAD_MARKET_VALUES(self, path=None):
        path = path or ut.SAVE_MARKET_PATH
        if os.path.exists(path):
            with open(path, 'rb') as file:
                loaded_dict = pickle.load(file)
            self.MARKET_INFO=loaded_dict

            dates = set()
            if 1 in self.MARKET_INFO and isinstance(self.MARKET_INFO[1], dict):
                dates.update(self.MARKET_INFO[1].keys())
            if 2 in self.MARKET_INFO and isinstance(self.MARKET_INFO[2], dict):
                dates.update(self.MARKET_INFO[2].keys())
            if dates:
                self._SET_FIRST_MARKET_DATE(dates)