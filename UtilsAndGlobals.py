from Const import *
import UtilsAndGlobals as ut
import FootballClasses as fc
from colorama import Fore, Back, Style
import unicodedata
import re
import difflib
import builtins
import inspect
import os

if not getattr(builtins, '_custom_print_installed', False):
    _original_print = builtins.print

    def _custom_print(*args, **kwargs):
        try:
            frame = inspect.currentframe().f_back
            filename = os.path.splitext(os.path.basename(frame.f_code.co_filename))[0]
            lineno = frame.f_lineno
            prefix = f"{filename}:{lineno}-"
            if args:
                first = str(args[0])
                prefix_nl = ""
                while first.startswith(("\n", "\r\n")):
                    if first.startswith("\r\n"):
                        prefix_nl += "\r\n"
                        first = first[2:]
                    else:
                        prefix_nl += "\n"
                        first = first[1:]
                new_first = f"{prefix_nl}{prefix}{first}"
                _original_print(new_first, *args[1:], **kwargs)
            else:
                _original_print(prefix, **kwargs)
        except Exception:
            _original_print(*args, **kwargs)

    builtins.print = _custom_print
    builtins._custom_print_installed = True

loadFromFile = True
loadMarket = True
loadReferees = True

CURRENT_MATCH_ID = 1
CURRENT_TEAM_ID = 0
TEAM_NAMES_TO_ID = {}
IDs_TO_TEAM = {}
SAVE_SEASONS_PATH = 'TestSave.csv'
INPUT_SEASONS_PATH = 'TestSave.csv'
SAVE_MARKET_PATH = 'market_values.pickle'
SAVE_REFEREES_PATH = 'Referees.pickle'
ALL_SEASONS_INFO = {}

#noTransferToGlobal = {}

def RAISE_IF(condition, error_message):
    if condition:
        RAISE(error_message)

def RAISE(error_message):
    raise Exception(error_message)
    
def CHECK_KEY_EXISTANCE(key, collection, newElement):
    if key in collection:
        return True
    collection[key] = newElement() if callable(newElement) else newElement
    return False

def GET_NORMALIZED_TEAM_NAME(equipo):
    ut.RAISE_IF(equipo not in NAMES_CORRECTION, f"{equipo} no está en la corrección")
    return NAMES_CORRECTION[equipo]

def GET_TRANSFERMARKT_TEAM_NAMES(equipo):
    equipoNames = ut.NAMES_TO_TRANSFERMARKT_NAMES[equipo]

def _clean_team_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8').lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    stopwords = {
        'rcd', 'ud', 'cf', 'sad', 'sd', 'ca', 'rc', 'fc', 'cd', 'up', 'ce', 'ad',
        'de', 'del', 'la', 'el', 'los', 'las', 'club', 'futbol'
    }
    tokens = [w for w in text.split() if w not in stopwords]
    return ' '.join(tokens)

def GET_GLOBAL_EQUIPO_ID_FROM_TRANSFERMARKT_NAME(equipoName, alternateEquipoName=None):
    # 1. Prioridad: Diccionario explícito existente (100% retrocompatible)
    for name in (equipoName, alternateEquipoName):
        if not name:
            continue
        if name in TRANSFERMARKT_NAMES_TO_NORMAL:
            target = TRANSFERMARKT_NAMES_TO_NORMAL[name]
            eq_id = GET_GLOBAL_EQUIPO_ID(target, False)
            if eq_id is not None:
                return eq_id
        if name in NAMES_CORRECTION:
            target = NAMES_CORRECTION[name]
            eq_id = GET_GLOBAL_EQUIPO_ID(target, False)
            if eq_id is not None:
                return eq_id
        if name in TEAM_NAMES_TO_ID:
            return TEAM_NAMES_TO_ID[name]

    # 2. Resolución inteligente por normalización de texto sobre equipos registrados
    names_to_try = [n for n in (equipoName, alternateEquipoName) if n]
    for n in names_to_try:
        clean_q = _clean_team_text(n)
        if not clean_q:
            continue

        # 2a. Comparación exacta de nombres limpios
        for team_name, team_id in TEAM_NAMES_TO_ID.items():
            if _clean_team_text(team_name) == clean_q:
                return team_id

        # 2b. Contención de tokens (ej: 'celta vigo' dentro de 'rc celta vigo')
        candidates = []
        for team_name, team_id in TEAM_NAMES_TO_ID.items():
            clean_team = _clean_team_text(team_name)
            if clean_team and (clean_team in clean_q or clean_q in clean_team):
                candidates.append((team_id, team_name))
        if len(candidates) == 1:
            return candidates[0][0]

        # 2c. Similitud difusa (fuzzy ratio >= 0.78)
        best_id = None
        best_ratio = 0.0
        for team_name, team_id in TEAM_NAMES_TO_ID.items():
            clean_team = _clean_team_text(team_name)
            ratio = difflib.SequenceMatcher(None, clean_q, clean_team).ratio()
            if ratio > best_ratio and ratio >= 0.78:
                best_ratio = ratio
                best_id = team_id
        if best_id is not None:
            return best_id

    # 3. Fallback tolerante: No romper el programa si un equipo es irreconocible
    print(Fore.YELLOW + f"  [AVISO] No se pudo emparejar el equipo de Transfermarkt: '{equipoName}' / '{alternateEquipoName}'" + Style.RESET_ALL)
    return None
    
'''def SAVENOTTRANSFER():
    global noTransferToGlobal
    with open('noTransferToGlobal.txt', 'w', encoding='utf-8') as f:
        f.write(f"{noTransferToGlobal}")'''

def GET_GLOBAL_EQUIPO_ID(equipoName, alta=True):
    if equipoName in TEAM_NAMES_TO_ID:
        return TEAM_NAMES_TO_ID[equipoName]
    if alta:
        global CURRENT_TEAM_ID
        CURRENT_TEAM_ID = CURRENT_TEAM_ID + 1
        TEAM_NAMES_TO_ID[equipoName] = CURRENT_TEAM_ID
        equipo = fc.Equipo(CURRENT_TEAM_ID, equipoName)
        IDs_TO_TEAM[CURRENT_TEAM_ID] = equipo
        return CURRENT_TEAM_ID
    else:
        return None
    

def ADD_SEASON_INFO(division, temporada, seasonInfo):
    ut.CHECK_KEY_EXISTANCE(division, ALL_SEASONS_INFO, {})
    ut.CHECK_KEY_EXISTANCE(temporada, ALL_SEASONS_INFO[division], seasonInfo)



_marketHelper = None
_refereesHelper = None

def get_market_helper():
    global _marketHelper
    if _marketHelper is None:
        from MarketHelper import MarketHelper
        _marketHelper = MarketHelper()
    return _marketHelper

def get_referees_helper():
    global _refereesHelper
    if _refereesHelper is None:
        from RefereesHelper import RefereesHelper
        _refereesHelper = RefereesHelper()
    return _refereesHelper

class _LazyHelperProxy:
    def __init__(self, getter):
        self._getter = getter
    def __getattr__(self, name):
        return getattr(self._getter(), name)

marketHelper = _LazyHelperProxy(get_market_helper)
refereesHelper = _LazyHelperProxy(get_referees_helper)

def configure(source='web', enable_market=True, enable_referees=True, output_path=None, input_path=None, market_path=None, referees_path=None):
    global loadFromFile, loadMarket, loadReferees, SAVE_SEASONS_PATH, INPUT_SEASONS_PATH, SAVE_MARKET_PATH, SAVE_REFEREES_PATH
    loadFromFile = (source == 'file')
    loadMarket = enable_market
    loadReferees = enable_referees
    if output_path:
        SAVE_SEASONS_PATH = output_path
    if input_path:
        INPUT_SEASONS_PATH = input_path
    if market_path:
        SAVE_MARKET_PATH = market_path
    if referees_path:
        SAVE_REFEREES_PATH = referees_path

def SAVE_MARKET_VALUES(path=None):
    if not loadMarket:
        return
    path = path or SAVE_MARKET_PATH
    get_market_helper().SAVE_MARKET_VALUES(path)
    
def SAVE_REFEREES_VALUES(path=None):
    if not loadReferees:
        return
    path = path or SAVE_REFEREES_PATH
    get_referees_helper().SAVE_REFEREES_VALUES(path)
    
def _writeHeaders(file, headersAndAttributes):
    file.write(';'.join(headersAndAttributes) + '\n')

def _writePartido(file, headersAndAttributes, partido):
    data = ';'.join(str(getattr(partido, attr, '')) for attr in headersAndAttributes)
    file.write(data + '\n')

def SAVE_ALL_SEASONS(fileName=None):
    fileName = fileName or SAVE_SEASONS_PATH
    fichero = open(fileName, 'w', encoding="utf-8")
    
    headersAndAttributes = ["idPartido", "division", "temporada", "jornada", "matchDate", "arbitroName", "arbitroId",
                            "localName", "localId", "localMarketValue", "puntosLocal",
                            "golesafavorlocal", "golesencontralocal", "visitanteName", "visitanteId",
                            "visitanteMarketValue", "puntosVisitante", "golesafavorvisitante", "golesencontravisitante",
                            "golesLocal", "golesVisitante", "golDiff"]
    _writeHeaders(fichero, headersAndAttributes)
    flat_partidos = [partido for division in ALL_SEASONS_INFO for temporada in ALL_SEASONS_INFO[division]
                    for jornada in ALL_SEASONS_INFO[division][temporada].jornadas
                    for partido in ALL_SEASONS_INFO[division][temporada].jornadas[jornada].values()]
    
    for partido in flat_partidos:
        _writePartido(fichero, headersAndAttributes, partido)

    fichero.close()