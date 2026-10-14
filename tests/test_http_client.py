import pytest
import requests

from src.football_dataset.http_client import HttpClient, HttpClientConfig, HttpError


class Response:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response


def test_retries_timeout_and_connection_error_until_exhausted():
    session = Session(
        [requests.Timeout("slow"), requests.ConnectionError("offline"), requests.Timeout("slow")]
    )
    sleeps = []
    client = HttpClient(
        HttpClientConfig(retries=2, backoff_factor=0.25, min_interval=0),
        session=session,
        sleep=sleeps.append,
    )

    with pytest.raises(HttpError, match="tras 3 intentos") as error:
        client.get("https://example.test")

    assert error.value.status_code is None
    assert len(session.calls) == 3
    assert sleeps == [0.25, 0.5]


def test_retry_after_takes_precedence_over_exponential_backoff():
    session = Session([Response(429, {"Retry-After": "7.5"}), Response(200)])
    sleeps = []
    client = HttpClient(
        HttpClientConfig(retries=1, backoff_factor=0.25, min_interval=0),
        session=session,
        sleep=sleeps.append,
    )

    assert client.get("https://example.test").status_code == 200
    assert sleeps == [7.5]


def test_retries_server_errors_and_raises_typed_error_after_limit():
    session = Session([Response(503), Response(500)])
    client = HttpClient(
        HttpClientConfig(retries=1, backoff_factor=0, min_interval=0),
        session=session,
        sleep=lambda _: None,
    )

    with pytest.raises(HttpError) as error:
        client.get("https://example.test")

    assert error.value.status_code == 500
    assert len(session.calls) == 2


@pytest.mark.parametrize("status", [403, 404, 418])
def test_non_retryable_or_unexpected_status_is_typed_error(status):
    client = HttpClient(
        HttpClientConfig(retries=3, min_interval=0),
        session=Session([Response(status)]),
    )

    with pytest.raises(HttpError) as error:
        client.get("https://example.test")

    assert error.value.status_code == status


def test_headers_timeout_and_request_parameters_are_forwarded():
    session = Session([Response(200)])
    client = HttpClient(
        HttpClientConfig(timeout=(1, 2), user_agent="test-agent", min_interval=0),
        session=session,
    )

    client.get("https://example.test", params={"page": 2})
    _, kwargs = session.calls[0]
    assert kwargs["headers"] == {"User-Agent": "test-agent"}
    assert kwargs["timeout"] == (1, 2)
    assert kwargs["params"] == {"page": 2}


def test_custom_user_agent_header_is_preserved():
    session = Session([Response(200)])
    client = HttpClient(HttpClientConfig(min_interval=0), session=session)

    client.get("https://example.test", headers={"User-Agent": "custom"})
    assert session.calls[0][1]["headers"]["User-Agent"] == "custom"


def test_rate_limit_uses_injected_clock_and_sleep():
    now = [10.0]
    sleeps = []
    session = Session([Response(200), Response(200)])
    client = HttpClient(
        HttpClientConfig(min_interval=5, retries=0),
        session=session,
        clock=lambda: now[0],
        sleep=lambda delay: (sleeps.append(delay), now.__setitem__(0, now[0] + delay)),
    )

    client.get("https://example.test")
    now[0] = 12.0
    client.get("https://example.test")

    assert sleeps == [3.0]
