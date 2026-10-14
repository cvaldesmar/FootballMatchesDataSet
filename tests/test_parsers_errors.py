from pathlib import Path

import pytest

from src.football_dataset.parsers import (
    BDFutbolCSVParser,
    BDFutbolParser,
    ParserError,
    TransfermarktMarketParser,
    TransfermarktRefereesParser,
)


def test_bdfutbol_rejects_missing_teams_and_matches():
    parser = BDFutbolParser()
    with pytest.raises(ParserError, match="equipos"):
        parser.parse('<div id="resultats"></div>')
    with pytest.raises(ParserError, match="partidos"):
        parser.parse('<div id="resultats">SE[1]="10|Barcelona";</div>')


@pytest.mark.parametrize(
    "html, message",
    [
        ('<div id="resultats">SE[1]="bad";</div>', "Equipo"),
        (
            '<div id="resultats">SE[1]="x|Barcelona";SP[1].push({"d":"12/09/2021","a1":"10","a2":"11","g1":"2","g2":"1"});</div>',
            "ID",
        ),
        (
            '<div id="resultats">SE[1]="10|Barcelona";SP[1].push({"d":"31/02/2021","a1":"10","a2":"11","g1":"2","g2":"1"});</div>',
            "Partido",
        ),
        (
            '<div id="resultats">SE[1]="10|Barcelona";SP[1].push({"d":"12/09/2021","a1":"10","a2":"11","g1":"2"});</div>',
            "campos obligatorios",
        ),
    ],
)
def test_bdfutbol_rejects_invalid_contracts(html, message):
    with pytest.raises(ParserError, match=message):
        BDFutbolParser().parse(html)


def test_csv_parser_rejects_missing_columns(tmp_path: Path):
    path = tmp_path / "invalid.csv"
    path.write_text("division;temporada\n1;2021-22\n", encoding="utf-8")

    with pytest.raises(ParserError, match="columnas obligatorias"):
        BDFutbolCSVParser().parse(path, 1, "2021-22")


@pytest.mark.parametrize(
    "row",
    [
        "1;2021-22;0;2021-09-12;A;1;B;2;1;0;1",
        "1;2021-22;1;not-a-date;A;1;B;2;1;0;1",
        "1;2021-22;1;2021-09-12;A;1;B;2;-1;0;-1",
        "1;2021-22;1;2021-09-12;A;1;B;2;1;0;0",
    ],
)
def test_csv_parser_rejects_invalid_rows(tmp_path: Path, row: str):
    path = tmp_path / "invalid.csv"
    header = "division;temporada;jornada;matchDate;localName;localId;visitanteName;visitanteId;golesLocal;golesVisitante;golDiff\n"
    path.write_text(header + row + "\n", encoding="utf-8")

    with pytest.raises(ParserError, match="Fila CSV inválida"):
        BDFutbolCSVParser().parse(path, 1, "2021-22")


def test_csv_parser_filters_other_division_and_season(tmp_path: Path):
    path = tmp_path / "matches.csv"
    header = "division;temporada;jornada;matchDate;localName;localId;visitanteName;visitanteId;golesLocal;golesVisitante;golDiff\n"
    rows = [
        "1;2021-22;1;2021-09-12;A;1;B;2;1;0;1",
        "2;2021-22;1;2021-09-12;C;3;D;4;1;0;1",
        "1;2020-21;1;2020-09-12;E;5;F;6;1;0;1",
    ]
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")

    result = BDFutbolCSVParser().parse(path, 1, "2021-22")
    assert len(result) == 1
    assert result[0]["localName"] == "A"


def test_transfermarkt_market_parser_rejects_missing_or_invalid_values():
    parser = TransfermarktMarketParser()
    with pytest.raises(ParserError, match="selector"):
        parser.parse_dates("<html></html>")
    with pytest.raises(ParserError, match="Fecha de mercado"):
        parser.parse_dates('<select class="chzn-select"><option value="bad">x</option></select>')
    with pytest.raises(ParserError, match="valores"):
        parser.parse_team_values("<html></html>")


def test_transfermarkt_referee_parser_rejects_missing_table_or_links():
    parser = TransfermarktRefereesParser()
    with pytest.raises(ParserError, match="tabla de árbitros"):
        parser.parse_referee_links("<html></html>")
    html = '<table class="items"><tr><th>Árbitros</th></tr><tr><td>sin enlace</td></tr></table>'
    with pytest.raises(ParserError, match="enlaces"):
        parser.parse_referee_links(html)
    with pytest.raises(ParserError, match="tabla de partidos"):
        parser.parse_matches('<div class="content-box-headline--logo"></div>', "Ref", 1)
