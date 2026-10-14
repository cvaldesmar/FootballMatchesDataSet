from pathlib import Path

import pytest

from src.football_dataset.context import ExecutionContext
from src.football_dataset.http_client import HttpClient, HttpClientConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def execution_context(tmp_path):
    return ExecutionContext(
        enable_market=False,
        enable_referees=False,
        input_path=str(FIXTURES_DIR / "matches.csv"),
        market_path=str(tmp_path / "market_values.json"),
        referees_path=str(tmp_path / "referees.json"),
    )


@pytest.fixture
def bdfutbol_html():
    return (FIXTURES_DIR / "bdfutbol.html").read_text(encoding="utf-8")


@pytest.fixture
def market_html():
    return (FIXTURES_DIR / "transfermarkt_market.html").read_text(encoding="utf-8")


@pytest.fixture
def referees_html():
    return (FIXTURES_DIR / "transfermarkt_referees.html").read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text, status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


@pytest.fixture
def fake_http_client():
    def factory(*responses):
        session = FakeSession(responses)
        client = HttpClient(
            HttpClientConfig(timeout=(1, 1), retries=0, min_interval=0),
            session=session,
        )
        return client, session

    return factory
