"""Parsers puros y validables de las fuentes externas."""

from .bdfutbol_parser import BDFutbolParser
from .csv_parser import BDFutbolCSVParser
from .errors import ParserError
from .transfermarkt_market_parser import TransfermarktMarketParser
from .transfermarkt_referees_parser import TransfermarktRefereesParser

__all__ = [
    "ParserError",
    "BDFutbolParser",
    "BDFutbolCSVParser",
    "TransfermarktMarketParser",
    "TransfermarktRefereesParser",
]
