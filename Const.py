#Autor original Ricardo Moya https://github.com/RicardoMoya/FootballMatchesDataSet
from datetime import datetime

SEASON_URL = "http://www.bdfutbol.com/es/t/t%s%s.html"
MARKET_URL = "https://www.transfermarkt.es/laliga/marktwerteverein/wettbewerb/ES%s/plus/?stichtag=%s"
REFEREES_URL = "https://www.transfermarkt.es/laliga/schiedsrichter/wettbewerb/ES%s/plus/?saison_id=%s"
REFEREES_MATCHES_URL = "https://www.transfermarkt.es%s/plus/0?funktion=1&saison_id=%s&wettbewerb_id=ES%s"

ALL_TEMPORADAS = ["1970-71", "1971-72", "1972-73", "1973-74", "1974-75", "1975-76", "1976-77", "1977-78", "1978-79", "1979-80", "1980-81", "1981-82", "1982-83", "1983-84", "1984-85", "1985-86", "1986-87", "1987-88", "1988-89", "1989-90", "1990-91", "1991-92", "1992-93", "1993-94", "1994-95", "1995-96", "1996-97", "1997-98", "1998-99", "1999-00", "2000-01", "2001-02", "2002-03", "2003-04", "2004-05", "2005-06", "2006-07", "2007-08", "2008-09", "2009-10", "2010-11", "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
SINCE_2000_TEMPORADAS = [t for t in ALL_TEMPORADAS if int(t.split("-")[0]) >= 2000]
SHORT_TEMPORADAS = ["2020-21", "2022-23", "2023-24", "2024-25", "2025-26"]
LAST_TEMPORADA = ["2025-26"]


NAMES_CORRECTION = {'AD Almería': 'Almería', 'AD Ceuta': 'AD Ceuta', 'Alavés': 'Alavés', 'Albacete': 'Albacete', 'Alcorcón': 'Alcorcón', 'Alcoyano': 'Alcoyano', 'Algeciras': 'Algeciras', 'Alicante': 'Alicante', 'Almería': 'Almería', 'Alzira': 'Alzira', 'Amorebieta': 'Amorebieta', 'Andorra': 'Andorra', 'Athletic Club': 'Athletic Club', 'Athletic Club B': 'Athletic Club B', 'Atlético Madrileño': 'Atlético de Madrid B', 'Atlético Marbella': 'Atlético Marbella', 'Atlético de Bilbao': 'Athletic Club', 'Atlético de Madrid': 'Atlético de Madrid', 'Atlético de Madrid B': 'Atlético de Madrid B', 'Avilés Industrial': 'Avilés Industrial', 'Badajoz': 'Badajoz', 'Baracaldo': 'Baracaldo', 'Barcelona': 'Barcelona', 'Barcelona Atlético': 'Barcelona B', 'Barcelona B': 'Barcelona B', 'Betis': 'Betis', 'Bilbao Athletic': 'Athletic Club', 'Burgos': 'Burgos CF', 'Burgos CF': 'Burgos CF', 'CD Málaga': 'Málaga', 'Calvo Sotelo': 'Calvo Sotelo', 'Cartagena': 'FC Cartagena', 'Castellón': 'Castellón', 'Castilla': 'Real Madrid Castilla', 'Celta de Vigo': 'Celta de Vigo', 'Ciudad de Murcia': 'Ciudad de Murcia', 'Compostela': 'Compostela', 'Cultural Leonesa': 'Cultural Leonesa', 'Cádiz': 'Cádiz', 'Córdoba': 'Córdoba', 'Deportivo Aragón': 'Deportivo Aragón', 'Deportivo de La Coruña': 'Deportivo de La Coruña', 'Écija': 'Écija', 'Eibar': 'Eibar', 'Elche': 'Elche', 'Ensidesa': 'Ensidesa', 'Espanyol': 'Espanyol', 'Español': 'Espanyol', 'Extremadura': 'Extremadura', 'Extremadura UD': 'Extremadura UD', 'FC Cartagena': 'FC Cartagena', 'Ferrol': 'Racing de Ferrol', 'Figueres': 'Figueres', 'Fuenlabrada': 'Fuenlabrada', 'Getafe': 'Getafe', 'Getafe Deportivo': 'Getafe', 'Gijón': 'Sporting de Gijón', 'Gimnàstic de Tarragona': 'Gimnàstic de Tarragona', 'Gimnástico de Tarragona': 'Gimnàstic de Tarragona', 'Girona': 'Girona', 'Granada': 'Granada', 'Granada 74': 'Granada 74', 'Guadalajara': 'Guadalajara', 'Huesca': 'Huesca', 'Hércules': 'Hércules', 'Ibiza': 'Ibiza', 'Jaén': 'Jaén', 'Langreo': 'Langreo', 'Las Palmas': 'Las Palmas', 'Leganés': 'Leganés', 'Levante': 'Levante', 'Linares CF': 'Linares CF', 'Llagostera': 'Llagostera', 'Lleida': 'Lleida', 'Logroñés': 'UD Logroñés', 'Lorca': 'Lorca', 'Lorca Deportiva': 'Lorca Deportiva', 'Lorca FC': 'Lorca FC', 'Lugo': 'Lugo', 'Mallorca': 'Mallorca', 'Mallorca B': 'Mallorca B', 'Mestalla': 'Mestalla', 'Mirandés': 'Mirandés', 'Mollerussa': 'Mollerussa', 'Moscardó': 'Moscardó', 'Murcia': 'Murcia', 'Málaga': 'Málaga', 'Málaga B': 'Málaga B', 'Mérida': 'Mérida', 'Numancia': 'Numancia', 'Onteniente': 'Onteniente', 'Orense': 'Ourense', 'Orihuela': 'Orihuela', 'Osasuna': 'Osasuna', 'Ourense': 'Ourense', 'Oviedo': 'Oviedo', 'Palamós': 'Palamós', 'Palencia CF': 'Palencia CF', 'Polideportivo Ejido': 'Polideportivo Ejido', 'Ponferradina': 'Ponferradina', 'Pontevedra': 'Pontevedra', 'Racing de Ferrol': 'Racing de Ferrol', 'Racing de Santander': 'Racing de Santander', 'Rayo Majadahonda': 'Rayo Majadahonda', 'Rayo Vallecano': 'Rayo Vallecano', 'Real Burgos': 'Burgos CF', 'Real Madrid': 'Real Madrid', 'Real Madrid B': 'Real Madrid Castilla', 'Real Madrid Castilla': 'Real Madrid Castilla', 'Real Sociedad': 'Real Sociedad', 'Real Sociedad B': 'Real Sociedad B', 'Real Unión': 'Real Unión', 'Recreativo de Huelva': 'Recreativo de Huelva', 'Reus': 'Reus', 'Sabadell': 'Sabadell', 'Salamanca': 'Salamanca', 'San Andrés': 'San Andrés', 'Santander': 'Racing de Santander', 'Sestao': 'Sestao', 'Sevilla': 'Sevilla', 'Sevilla Atlético': 'Sevilla Atlético', 'Sporting de Gijón': 'Sporting de Gijón', 'Tarrasa': 'Tarrasa', 'Tenerife': 'Tenerife', 'Terrassa': 'Terrassa', 'Toledo': 'Toledo', 'UCAM Murcia': 'UCAM Murcia', 'UD Logroñés': 'UD Logroñés', 'Universidad de Las Palmas': 'Universidad de Las Palmas', 'Valencia': 'Valencia', 'Valladolid': 'Valladolid', 'Vecindario': 'Vecindario', 'Villarreal': 'Villarreal', 'Villarreal B': 'Villarreal B', 'Xerez': 'Xerez', 'Zaragoza': 'Zaragoza'}

NAMES_TO_TRANSFERMARKT_NAMES = {
    'Alavés': ['Deportivo Alavés', 'Alavés'],
    'Albacete': 'Albacete Balompié',
    'Alcorcón': 'AD Alcorcón',
    'Almería': 'UD Almería',
    'Andorra': 'FC Andorra',
    'Athletic Club': ['Athletic Club', 'Athletic Bilbao'],
    'Atlético de Madrid': ['Club Atlético de Madrid', 'Atlético de Madrid', 'Atlético Madrid'],
    'Barcelona': 'FC Barcelona',
    'Betis': ['Real Betis Balompié', 'Real Betis'],
    'Cartagena': 'FC Cartagena',
    'Castellón': 'CD Castellón',
    'Celta de Vigo': ['RC Celta de Vigo', 'Celta de Vigo', 'RC Celta'],
    'Cádiz': 'Cádiz CF',
    'Deportivo de La Coruña': ['Deportivo Coruña', 'RC Deportivo Coruña', 'RC Deportivo de La Coruña'],
    'Eibar': 'SD Eibar',
    'Elche': 'Elche CF',
    'Espanyol': ['Español', 'RCD Espanyol', 'RCD Espanyol Barcelona', 'RCD Espanyol de Barcelona'],
    'Getafe': 'Getafe CF',
    'Girona': 'Girona FC',
    'Granada': 'Granada CF',
    'Hércules': 'Hércules CF',
    'Huesca': 'SD Huesca',
    'Ibiza': 'UD Ibiza',
    'Las Palmas': 'UD Las Palmas',
    'Langreo': 'UP Langreo',
    'Leganés': 'CD Leganés',
    'Levante': 'Levante UD',
    'Lugo': 'CD Lugo',
    'Málaga': 'CD Málaga',
    'Mallorca': ['RCD Mallorca', 'Mallorca'],
    'Mirandés': 'CD Mirandés',
    'Osasuna': ['CA Osasuna', 'Osasuna'],
    'Oviedo': 'Real Oviedo',
    'Ponferradina': 'SD Ponferradina',
    'Racing de Santander': ['Santander', 'Racing', 'Real Racing Club'],
    'Rayo Vallecano': ['Rayo Vallecano de Madrid', 'Rayo Vallecano'],
    'Real Madrid': ['Real Madrid CF', 'Real Madrid'],
    'Real Sociedad': ['Real Sociedad de Fútbol', 'Real Sociedad'],
    'Sevilla': 'Sevilla FC',
    'Sporting de Gijón': ['Real Sporting de Gijón', 'Real Sporting', 'Sporting de Gijón', 'Sporting Gijón'],
    'Tenerife': 'CD Tenerife',
    'UD Logroñés': 'CD Logroñés',
    'Valencia': 'Valencia CF',
    'Valladolid': 'Real Valladolid CF',
    'Villarreal': 'Villarreal CF',
    'Villarreal B': 'Villarreal CF B',
    'Zaragoza': 'Real Zaragoza',
    'Córdoba': 'Córdoba CF',
    'Xerez': 'Xerez CD',
    'Racing de Ferrol': 'Racing Ferrol',
    'Gimnàstic de Tarragona': 'Tarragona',
    'Murcia': 'Real Murcia',
    'Salamanca': 'UD Salamanca',
    'Ourense': 'Orense',
    'Barcelona B': 'FC Barcelona Atlético',
    'Jaén': 'Real Jaén CF',
    'Algeciras': 'Algeciras CF',
    'Numancia': 'CD Numancia',
    'Sabadell': 'CE Sabadell'
}

TRANSFERMARKT_NAMES_TO_NORMAL = {item: key for key, value in NAMES_TO_TRANSFERMARKT_NAMES.items() for item in (value if isinstance(value, list) else [value])}

# sorted_dict = {k: v for k, v in sorted(MARKET_NAMES_CORRECTION.items())}
# print(str(sorted_dict))
TIED_TEMPORADAS = ["1970-71","1974-75","1978-79","1980-81","1983-84","1993-94","2004-05","2006-07","2020-21","2021-22"]
TIED_SEASON_WINNERS = {
    1:{
        "1970-71":"Valencia",
        "1980-81":"Real Sociedad",
        "1983-84":"Athletic Club",
        "1993-94":"Barcelona",
        "2006-07":"Real Madrid"},
    2:{
        "1974-75":"Oviedo",
        "1978-79":"Almería",
        "1980-81":"Castellón",
        "1983-84":"Real Madrid Castilla",
        "2004-05":"Cádiz",
        "2020-21":"Espanyol",
        "2021-22":"Almería",}
}