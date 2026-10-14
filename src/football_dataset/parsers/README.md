# Parsers

Los parsers reciben HTML/CSV y devuelven modelos o diccionarios validados. No realizan peticiones HTTP ni modifican registros globales. Los cambios de estructura de una fuente externa deben producir [`ParserError`](errors.py:1) con contexto.

## Parsers disponibles

- [`BDFutbolParser`](bdfutbol_parser.py:11): equipos y partidos embebidos en el HTML/JavaScript de BDFutbol.
- [`BDFutbolCSVParser`](csv_parser.py:10): filas filtradas por división y temporada desde el CSV local.
- [`TransfermarktMarketParser`](transfermarkt_market_parser.py:9): fechas de valoración y valores de equipos.
- [`TransfermarktRefereesParser`](transfermarkt_referees_parser.py:9): enlaces de árbitros y partidos arbitrados.

Los modelos estructurados están en [`models.py`](../models.py:1): [`RawTeam`](../models.py:7), [`RawMatch`](../models.py:13), [`MarketValue`](../models.py:23) y [`RefereeMatch`](../models.py:29).