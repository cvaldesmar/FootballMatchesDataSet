"""Valores de mercado de Transfermarkt sin singletons ni estado global."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from . import Const as const
from .context import ExecutionContext
from .http_client import HttpClient
from .parsers import TransfermarktMarketParser
from .persistence import atomic_json_dump, load_versioned_json

logger = logging.getLogger(__name__)
CACHE_VERSION = 3


class MarketHelper:
    def __init__(
        self,
        context: ExecutionContext,
        http_client: HttpClient | None = None,
        parser: TransfermarktMarketParser | None = None,
    ):
        self.context = context
        self.http_client = http_client or HttpClient()
        self.parser = parser or TransfermarktMarketParser()
        self.market_info: dict[int, dict[date, dict[str, float]]] = {}
        self.team_market_info: dict[str, dict[date, float]] = {}
        self.first_market_date: date | None = None
        if context.enable_market:
            self.load_values(context.market_path)

    def ensure_division_dates(self, division: int) -> None:
        if not self.context.enable_market or self.market_info.get(division):
            return
        response = self.http_client.get(const.MARKET_URL % (division, ""))
        dates = self.parser.parse_dates(response.text)
        self.market_info[division] = dates
        self._set_first_date(dates)

    def scrape_team_values(self, division: int, market_date: date) -> dict[str, float]:
        response = self.http_client.get(
            const.MARKET_URL % (division, market_date.strftime("%Y-%m-%d"))
        )
        return self.parser.parse_team_values(response.text)

    def getTeamsMarketValue(
        self, division: int, match_date: str | date, local_name: str, away_name: str
    ) -> tuple[float, float]:
        if not self.context.enable_market:
            return -1, -1
        return self._get_market_value(division, local_name, match_date), self._get_market_value(
            division, away_name, match_date
        )

    def _get_market_value(self, division: int, team_name: str, match_date: str | date) -> float:
        match_day = (
            datetime.strptime(match_date, "%Y-%m-%d").date()
            if isinstance(match_date, str)
            else match_date
        )
        cached = self._cached_team_value(team_name, match_day)
        if cached is not None:
            return cached
        self.ensure_division_dates(division)
        if not self.market_info.get(division):
            return -1
        candidates = [d for d in self.market_info[division] if d <= match_day]
        market_day = (
            max(candidates)
            if candidates
            else min(self.market_info[division], key=lambda d: abs((d - match_day).days))
        )
        values = self.market_info[division].get(market_day)
        if not values:
            values = self.scrape_team_values(division, market_day)
            self.market_info[division][market_day] = values
        names = self._candidate_names(team_name)
        for candidate in names:
            if candidate in values:
                return values[candidate]
        for candidate in names:
            clean = self._clean(candidate)
            for name, value in values.items():
                if (
                    clean == self._clean(name)
                    or clean in self._clean(name)
                    or self._clean(name) in clean
                ):
                    return value
        return -1

    @staticmethod
    def _clean(value: str) -> str:
        import unicodedata

        text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
        return " ".join(
            word
            for word in text.replace("-", " ").split()
            if word not in {"fc", "cf", "ud", "rcd", "cd", "real", "club"}
        )

    def _candidate_names(self, name: str) -> list[str]:
        mapped = const.NAMES_TO_TRANSFERMARKT_NAMES.get(name, name)
        values = [str(value) for value in mapped] if isinstance(mapped, list) else [str(mapped)]
        if name not in values:
            values.append(name)
        return values

    def _set_first_date(self, dates: dict[date, dict[str, float]]) -> None:
        if dates:
            value = min(dates)
            self.first_market_date = (
                value if self.first_market_date is None else min(self.first_market_date, value)
            )

    def _cached_team_value(self, team_name: str, match_day: date) -> float | None:
        candidates = self._candidate_names(team_name)
        for candidate in candidates:
            dates = self.team_market_info.get(candidate)
            if not dates:
                continue
            available = [day for day in dates if day <= match_day]
            if available:
                return dates[max(available)]
        return None

    def save_values(self, path: str | Path | None = None) -> None:
        path = path or self.context.market_path
        team_cache: dict[str, dict[str, float]] = {}
        for values_by_date in self.market_info.values():
            for day, values in values_by_date.items():
                for team_name, value in values.items():
                    team_cache.setdefault(team_name, {})
                    # El último valor recorrido prevalece deliberadamente.
                    team_cache[team_name][day.isoformat()] = float(value)
        for team_name, dates in self.team_market_info.items():
            team_cache.setdefault(team_name, {}).update(
                {day.isoformat(): float(value) for day, value in dates.items()}
            )
        atomic_json_dump(path, {"version": CACHE_VERSION, "cache": team_cache})

    def load_values(self, path: str | Path | None = None) -> None:
        path = path or self.context.market_path
        try:
            payload = load_versioned_json(
                path,
                cache_name="mercado",
                current_version=CACHE_VERSION,
            )
            if payload is None:
                return
            cache = payload["cache"]
            if cache and all(str(key).isdigit() for key in cache):
                self.market_info = {
                    int(div): {
                        datetime.strptime(day, "%Y-%m-%d").date(): values
                        for day, values in dates.items()
                    }
                    for div, dates in cache.items()
                }
                for values in self.market_info.values():
                    self._set_first_date(values)
            else:
                self.team_market_info = {
                    team: {
                        datetime.strptime(day, "%Y-%m-%d").date(): float(value)
                        for day, value in dates.items()
                    }
                    for team, dates in cache.items()
                }
        except (OSError, ValueError, TypeError) as error:
            logger.warning("No se pudo cargar la caché de mercado %s: %s", path, error)

    # Compatibilidad con el nombre histórico.
    SAVE_MARKET_VALUES = save_values
    _LOAD_MARKET_VALUES = load_values
