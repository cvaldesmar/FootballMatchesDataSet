import csv
from datetime import date
from types import SimpleNamespace

from src.football_dataset.dataset_io import (
    HEADERS,
    SCHEMA_METADATA_PREFIX,
    append_season,
    write_csv_header,
)
from src.football_dataset.DatosTemporada import DatosTemporada
from src.football_dataset.FootballClasses import Equipo, Partido
from src.football_dataset.MarketHelper import MarketHelper
from src.football_dataset.models import RawMatch, RawTeam
from src.football_dataset.parsers import (
    BDFutbolParser,
    TransfermarktMarketParser,
    TransfermarktRefereesParser,
)
from src.football_dataset.RefereesHelper import RefereesHelper
from src.football_dataset.UtilsAndGlobals import (
    GET_GLOBAL_EQUIPO_ID_FROM_TRANSFERMARKT_NAME,
    GET_NORMALIZED_TEAM_NAME,
)


def test_models_construct_and_serialize():
    team = Equipo(1, "Barcelona", 500)
    assert team.idGlobalClub == 1
    assert "Barcelona" in str(team)

    match = Partido(
        idPartido=1,
        division=1,
        temporada="2021-22",
        jornada=1,
        matchDate="2021-09-12",
        arbitroName="",
        arbitroId=-1,
        localName="Barcelona",
        localId=1,
        localMarketValue=-1,
        puntosLocal=0,
        golesafavorlocal=0,
        golesencontralocal=0,
        visitanteName="Real Madrid",
        visitanteId=2,
        visitanteMarketValue=-1,
        puntosVisitante=0,
        golesafavorvisitante=0,
        golesencontravisitante=0,
        golesLocal=2,
        golesVisitante=1,
        golDiff=1,
        posicionLocal=1,
        posicionVisitante=2,
        diferenciaPuntos=0,
        distanciaKm=0,
    )
    assert match.matchDate == date(2021, 9, 12)
    assert "1::1::2021-22" in str(match)


def test_team_name_normalization_and_resolution(execution_context):
    assert GET_NORMALIZED_TEAM_NAME("Barcelona") == "Barcelona"
    execution_context.get_or_create_team("Barcelona")
    assert GET_GLOBAL_EQUIPO_ID_FROM_TRANSFERMARKT_NAME(execution_context, "FC Barcelona") == 1


def test_standings_accumulate_before_next_match(execution_context):
    class Loader:
        teamsSeasonIdToGlobalIdDict = {10: 1, 11: 2}
        matchesArray = [[1, "2021-09-12", 1, "Barcelona", 2, "Real Madrid", 2, 1, 1]]

    execution_context.get_or_create_team("Barcelona")
    execution_context.get_or_create_team("Real Madrid")
    season = DatosTemporada(
        1,
        "2021-22",
        context=execution_context,
        season_loader=Loader(),
        market_helper=type("Market", (), {"getTeamsMarketValue": lambda *args: (-1, -1)})(),
        referees_helper=type(
            "Referees", (), {"getMatchRefereeAndResults": lambda *args: ("", -1, "")}
        )(),
    )
    season.addMatch(1, 2, "2021-09-19", 2, "Real Madrid", 1, "Barcelona", 0, 0, 0)

    matches = list(season.jornadas[1].values()) + list(season.jornadas[2].values())
    assert matches[0].puntosLocal == 0
    assert matches[1].puntosLocal == 0
    assert season.clasificacion[1] == 4
    assert season.clasificacion[2] == 1


def test_historical_features_are_frozen_within_a_matchday(execution_context):
    class Loader:
        teamsSeasonIdToGlobalIdDict = {10: 1, 11: 2, 12: 3}
        matchesArray = [
            [1, "2021-09-12", 1, "Barcelona", 2, "Real Madrid", 2, 1, 1],
            [1, "2021-09-12", 3, "Valencia", 1, "Barcelona", 0, 0, 0],
            [2, "2021-09-19", 2, "Real Madrid", 3, "Valencia", 1, 0, 1],
        ]

    for name in ("Barcelona", "Real Madrid", "Valencia"):
        execution_context.get_or_create_team(name)
    season = DatosTemporada(
        1,
        "2021-22",
        context=execution_context,
        season_loader=Loader(),
        market_helper=type("Market", (), {"getTeamsMarketValue": lambda *args: (-1, -1)})(),
        referees_helper=type(
            "Referees", (), {"getMatchRefereeAndResults": lambda *args: ("", -1, "")}
        )(),
    )

    first_round = list(season.jornadas[1].values())
    assert [(match.puntosLocal, match.puntosVisitante) for match in first_round] == [(0, 0), (0, 0)]
    assert [(match.posicionLocal, match.posicionVisitante) for match in first_round] == [
        (1, 2),
        (3, 1),
    ]
    assert all(
        match.diferenciaPuntos == match.puntosLocal - match.puntosVisitante for match in first_round
    )
    second_round_match = next(iter(season.jornadas[2].values()))
    assert second_round_match.puntosLocal == 0
    assert second_round_match.puntosVisitante == 1
    assert (second_round_match.posicionLocal, second_round_match.posicionVisitante) == (3, 2)


def test_form_and_h2h_use_only_previous_matches(execution_context):
    class Loader:
        teamsSeasonIdToGlobalIdDict = {10: 1, 11: 2}
        matchesArray = [
            [1, "2021-09-12", 1, "Barcelona", 2, "Real Madrid", 2, 0, 2],
            [2, "2021-09-19", 2, "Real Madrid", 1, "Barcelona", 1, 0, 1],
            [3, "2021-09-26", 1, "Barcelona", 2, "Real Madrid", 3, 0, 3],
            [4, "2021-10-03", 2, "Real Madrid", 1, "Barcelona", 2, 0, 2],
            [5, "2021-10-10", 1, "Barcelona", 2, "Real Madrid", 1, 0, 1],
            [6, "2021-10-17", 2, "Real Madrid", 1, "Barcelona", 1, 0, 1],
            [7, "2021-10-24", 1, "Barcelona", 2, "Real Madrid", 2, 0, 2],
        ]

    execution_context.get_or_create_team("Barcelona")
    execution_context.get_or_create_team("Real Madrid")
    season = DatosTemporada(
        1,
        "2021-22",
        context=execution_context,
        season_loader=Loader(),
        market_helper=type("Market", (), {"getTeamsMarketValue": lambda *args: (-1, -1)})(),
        referees_helper=type(
            "Referees", (), {"getMatchRefereeAndResults": lambda *args: ("", -1, "")}
        )(),
    )

    first = next(iter(season.jornadas[1].values()))
    assert first.formaLocal == ""
    assert first.rachaLocal == 0
    assert first.h2hMatches == 0

    second = next(iter(season.jornadas[2].values()))
    assert second.formaLocal == "L"
    assert second.rachaLocal == 0
    assert second.h2hLocalWins == 0
    assert second.h2hAwayWins == 1
    assert second.h2hMatches == 1

    third = next(iter(season.jornadas[3].values()))
    assert third.formaLocal == "WL"
    assert third.rachaLocal == 3
    assert (third.h2hLocalWins, third.h2hDraws, third.h2hAwayWins, third.h2hMatches) == (1, 0, 1, 2)

    all_matches = [match for jornada in season.jornadas.values() for match in jornada.values()]
    assert all(
        len(match.formaLocal) <= 5 and len(match.formaVisitante) <= 5 for match in all_matches
    )
    assert all(match.h2hMatches <= 5 for match in all_matches)


def test_competitive_context_detects_champion_and_confirmed_relegation(execution_context):
    class Loader:
        teamsSeasonIdToGlobalIdDict = {10: 1, 11: 2, 12: 3, 13: 4}
        matchesArray = [[1, "2021-09-12", 1, "Barcelona", 2, "Real Madrid", 1, 0, 1]]

    for name in ("Barcelona", "Real Madrid", "Valencia", "Sevilla"):
        execution_context.get_or_create_team(name)
    season = DatosTemporada(
        1,
        "2021-22",
        context=execution_context,
        season_loader=Loader(),
        market_helper=type("Market", (), {"getTeamsMarketValue": lambda *args: (-1, -1)})(),
        referees_helper=type(
            "Referees", (), {"getMatchRefereeAndResults": lambda *args: ("", -1, "")}
        )(),
    )
    season.numJornadas = 2
    standings = {
        1: (1, 6, 8, 0),
        2: (2, 0, 1, 4),
        3: (3, 0, 0, 4),
        4: (4, 0, 0, 5),
    }

    context = season._compute_competitive_context(2, standings)
    assert context["campeon_id"] == 1
    assert context["teams"][4]["descenso"] == 1
    assert context["teams"][1]["presion"] == 0


def test_competitive_context_is_attached_before_current_result(execution_context):
    class Loader:
        teamsSeasonIdToGlobalIdDict = {10: 1, 11: 2}
        matchesArray = [[1, "2021-09-12", 1, "Barcelona", 2, "Real Madrid", 5, 0, 5]]

    execution_context.get_or_create_team("Barcelona")
    execution_context.get_or_create_team("Real Madrid")
    season = DatosTemporada(
        1,
        "2021-22",
        context=execution_context,
        season_loader=Loader(),
        market_helper=type("Market", (), {"getTeamsMarketValue": lambda *args: (-1, -1)})(),
        referees_helper=type(
            "Referees", (), {"getMatchRefereeAndResults": lambda *args: ("", -1, "")}
        )(),
    )

    match = next(iter(season.jornadas[1].values()))
    assert match.campeonId == -1
    assert match.descensoConfirmadoLocal == 0
    assert match.descensoConfirmadoVisitante == 0
    assert 0 <= match.presionLocal <= 3
    assert 0 <= match.presionVisitante <= 3


def test_rivalry_flag_marks_classics_and_is_symmetric(execution_context):
    class Loader:
        teamsSeasonIdToGlobalIdDict = {10: 1, 11: 2, 12: 3}
        matchesArray = [
            [1, "2021-09-12", 1, "Barcelona", 2, "Real Madrid", 0, 0, 0],
            [2, "2021-09-19", 2, "Real Madrid", 1, "Barcelona", 0, 0, 0],
            [3, "2021-09-26", 1, "Barcelona", 3, "Valencia", 0, 0, 0],
        ]

    for name in ("Barcelona", "Real Madrid", "Valencia"):
        execution_context.get_or_create_team(name)
    season = DatosTemporada(
        1,
        "2021-22",
        context=execution_context,
        season_loader=Loader(),
        market_helper=type("Market", (), {"getTeamsMarketValue": lambda *args: (-1, -1)})(),
        referees_helper=type(
            "Referees", (), {"getMatchRefereeAndResults": lambda *args: ("", -1, "")}
        )(),
    )

    first, second, third = (next(iter(season.jornadas[number].values())) for number in (1, 2, 3))
    assert first.rivalidad == 1
    assert second.rivalidad == 1
    assert third.rivalidad == 0


def test_incremental_csv_writes_header_once_and_appends_seasons(tmp_path):
    path = tmp_path / "dataset.csv"
    match = SimpleNamespace(**{header: str(index) for index, header in enumerate(HEADERS)})
    season = SimpleNamespace(jornadas={1: {1: match}})

    write_csv_header(path)
    assert append_season(path, season) == 1
    assert append_season(path, season) == 1

    with path.open(encoding="utf-8", newline="") as file:
        assert file.readline().strip() == SCHEMA_METADATA_PREFIX
        rows = list(csv.DictReader(file, delimiter=";"))
    assert list(rows[0]) == HEADERS
    assert len(rows) == 2
    assert rows[0]["rivalidad"] == str(HEADERS.index("rivalidad"))


def test_parsers_consume_local_fixtures(bdfutbol_html, market_html, referees_html):
    teams, matches = BDFutbolParser().parse(bdfutbol_html)
    assert teams == [RawTeam(10, "Barcelona"), RawTeam(11, "Real Madrid")]
    assert matches == [RawMatch(1, date(2021, 9, 12), 10, 11, 2, 1)]
    assert TransfermarktMarketParser().parse_dates(market_html)
    assert TransfermarktMarketParser().parse_team_values(market_html)["FC Barcelona"] == 500.0
    assert TransfermarktRefereesParser().parse_referee_links(referees_html)


def test_market_cache_round_trip(execution_context, tmp_path):
    path = tmp_path / "market.json"
    helper = MarketHelper(execution_context)
    helper.market_info = {1: {date(2021, 8, 1): {"Barcelona": 500.0}}}
    helper.save_values(path)

    loaded = MarketHelper(execution_context)
    loaded.load_values(path)
    assert loaded.team_market_info["Barcelona"][date(2021, 8, 1)] == 500.0


def test_referee_cache_round_trip(execution_context, tmp_path):
    path = tmp_path / "referees.json"
    helper = RefereesHelper(execution_context)
    helper.season_division_matches = {"2021": {"1": {"key": ["Ref", 1, "2:1"]}}}
    helper.save_values(path)

    loaded = RefereesHelper(execution_context)
    loaded.load_values(path)
    assert loaded.season_division_matches["2021"]["1"]["key"] == ["Ref", 1, "2:1"]
