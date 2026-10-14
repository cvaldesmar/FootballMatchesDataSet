from datetime import date

import pytest

from src.football_dataset.context import ExecutionContext
from src.football_dataset.http_client import HttpClient, HttpClientConfig, HttpError
from src.football_dataset.models import RawMatch
from src.football_dataset.parsers import BDFutbolCSVParser, BDFutbolParser, ParserError
from src.football_dataset.validation import DatasetValidator


def test_context_isolated_and_team_ids_are_local():
    first = ExecutionContext()
    second = ExecutionContext()
    assert first.get_or_create_team("Barcelona") == 1
    assert first.next_match_id() == 1
    assert second.get_or_create_team("Barcelona") == 1
    assert second.current_match_id == 1


def test_bdfutbol_parser_validates_embedded_data():
    html = """<div id="resultats">SE[1]="10|Barcelona";SP[1].push({"d":"12/09/2021","a1":"10","a2":"11","g1":"2","g2":"1"});</div>"""
    teams, matches = BDFutbolParser().parse(html)
    assert teams[0].name == "Barcelona"
    assert matches[0] == RawMatch(1, date(2021, 9, 12), 10, 11, 2, 1)


def test_bdfutbol_parser_rejects_missing_structure():
    with pytest.raises(ParserError, match="resultats"):
        BDFutbolParser().parse("<html></html>")


def test_validator_detects_duplicate_and_inconsistent_score():
    match = {
        "jornada": 1,
        "localId": 1,
        "visitanteId": 2,
        "matchDate": "2021-09-12",
        "golesLocal": 2,
        "golesVisitante": 1,
        "golDiff": 0,
    }
    report = DatasetValidator().validate_matches(
        [match, match], expected_teams=2, expected_matches=2
    )
    assert not report.valid
    assert {issue.code for issue in report.errors} == {"duplicate_match", "inconsistent_goal_diff"}


def test_http_client_uses_timeout_and_raises_typed_http_error():
    class Response:
        status_code = 403
        headers = {}

    class Session:
        def get(self, *args, **kwargs):
            assert kwargs["timeout"] == (1, 2)
            return Response()

    client = HttpClient(HttpClientConfig(timeout=(1, 2), retries=0), session=Session())
    with pytest.raises(HttpError) as error:
        client.get("https://example.test")
    assert error.value.status_code == 403


def test_csv_parser_rejects_inconsistent_goal_difference(tmp_path):
    path = tmp_path / "matches.csv"
    path.write_text(
        "division;temporada;jornada;matchDate;localName;localId;visitanteName;visitanteId;golesLocal;golesVisitante;golDiff\n1;2021-22;1;2021-09-12;Barcelona;1;Real Madrid;2;2;1;0\n",
        encoding="utf-8",
    )
    with pytest.raises(ParserError, match="golDiff"):
        BDFutbolCSVParser().parse(path, 1, "2021-22")
