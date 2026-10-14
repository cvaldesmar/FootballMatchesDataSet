"""Cliente HTTP compartido con timeout, reintentos y limitación de frecuencia."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests
from requests import Response


class HttpError(RuntimeError):
    """Error controlado al descargar una fuente externa."""

    def __init__(self, message: str, *, url: str, status_code: int | None = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


@dataclass(frozen=True)
class HttpClientConfig:
    timeout: tuple[float, float] = (10.0, 30.0)
    retries: int = 3
    backoff_factor: float = 0.5
    min_interval: float = 0.25
    user_agent: str = "FootballMatchesDataSet/1.0 (+https://github.com/)"


class HttpClient:
    """Wrapper pequeño y testeable alrededor de ``requests.Session``."""

    def __init__(
        self,
        config: HttpClientConfig | None = None,
        session: Any = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.config = config or HttpClientConfig()
        self.session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None

    def get(self, url: str, **kwargs: Any) -> Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("User-Agent", self.config.user_agent)
        timeout = kwargs.pop("timeout", self.config.timeout)
        attempts = max(1, self.config.retries + 1)
        last_error: Exception | None = None

        for attempt in range(attempts):
            self._wait_for_rate_limit()
            try:
                response = self.session.get(url, headers=headers, timeout=timeout, **kwargs)
                self._last_request_at = self._clock()
                if response.status_code == 200:
                    return response
                if response.status_code in {403, 404}:
                    raise HttpError(
                        f"HTTP {response.status_code} al acceder a {url}",
                        url=url,
                        status_code=response.status_code,
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < attempts - 1:
                        self._sleep(self._retry_delay(attempt, response))
                        continue
                    raise HttpError(
                        f"HTTP {response.status_code} tras {attempts} intentos: {url}",
                        url=url,
                        status_code=response.status_code,
                    )
                raise HttpError(
                    f"HTTP inesperado {response.status_code} al acceder a {url}",
                    url=url,
                    status_code=response.status_code,
                )
            except HttpError:
                raise
            except (requests.Timeout, requests.ConnectionError) as error:
                last_error = error
                if attempt >= attempts - 1:
                    raise HttpError(
                        f"No se pudo acceder a {url} tras {attempts} intentos: {error}",
                        url=url,
                    ) from error
                self._sleep(self._retry_delay(attempt))

        raise HttpError(f"Error HTTP desconocido al acceder a {url}: {last_error}", url=url)

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = self._clock() - self._last_request_at
        remaining = self.config.min_interval - elapsed
        if remaining > 0:
            self._sleep(remaining)

    def _retry_delay(self, attempt: int, response: Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
        return float(self.config.backoff_factor * (2**attempt))
