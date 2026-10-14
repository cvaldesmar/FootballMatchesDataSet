import pytest

from src.football_dataset.context import ExecutionContext
from src.football_dataset.http_client import HttpClient, HttpClientConfig, HttpError
from src.football_dataset.MarketHelper import MarketHelper
from src.football_dataset.RefereesHelper import RefereesHelper
from src.football_dataset.WebScraper import WebScraper

pytestmark = pytest.mark.integration


def test_real_bdfutbol_scraping():
    context = ExecutionContext(enable_market=False, enable_referees=False)
    try:
        scraper = WebScraper(
            1,
            "2021-22",
            context=context,
            http_client=HttpClient(HttpClientConfig(min_interval=0.5)),
        )
    except HttpError as error:
        if error.status_code in {403, 429} or error.status_code is None:
            pytest.skip(f"BDFutbol no disponible desde este entorno: {error}")
        raise
    assert scraper.teamsSeasonIdToGlobalIdDict
    assert scraper.matchesArray


def test_real_transfermarkt_scraping():
    context = ExecutionContext(enable_market=True, enable_referees=False)
    try:
        helper = MarketHelper(context, http_client=HttpClient(HttpClientConfig(min_interval=0.5)))
        helper.ensure_division_dates(1)
    except HttpError as error:
        if error.status_code in {403, 429} or error.status_code is None:
            pytest.skip(f"Transfermarkt no disponible desde este entorno: {error}")
        raise
    assert helper.market_info[1]


def test_real_transfermarkt_referees_scraping():
    context = ExecutionContext(enable_market=False, enable_referees=True)
    try:
        helper = RefereesHelper(context, http_client=HttpClient(HttpClientConfig(min_interval=0.5)))
        result = helper.getMatchRefereeAndResults(
            2021, 1, "2021-08-15", "Barcelona", "Real Sociedad"
        )
    except HttpError as error:
        if error.status_code in {403, 429} or error.status_code is None:
            pytest.skip(f"Transfermarkt no disponible desde este entorno: {error}")
        raise
    assert isinstance(result, tuple)
