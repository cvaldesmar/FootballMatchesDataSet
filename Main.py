#Autor original Ricardo Moya https://github.com/RicardoMoya/FootballMatchesDataSet

from ScrapeBDClass import ScrapeBDFutbol

scrapeBD = ScrapeBDFutbol()
scrapeBD.startScrape()
scrapeBD.saveInfo('DataSetPartidos.txt')

#
# from ScrapBDFutbol import *
# # Obtengo los partidos de futbol de las temporadas anteriores
# partidos = getInfo()
# fichero = open('DataSetPartidos.txt', 'w')
# fichero.write('idPartido::temporada::division::jornada::EquipoLocal::'
#               'EquipoVisitante::golesLocal::golesVisitante::fecha::timestamp\n')
# for value in partidos.values():
#     fichero.write('%s\n' % str(value))
#
# fichero.close()