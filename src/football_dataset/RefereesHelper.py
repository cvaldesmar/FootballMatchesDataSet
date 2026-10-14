"""Árbitros de Transfermarkt sin singleton global."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from . import Const as const
from .context import ExecutionContext
from .http_client import HttpClient
from .parsers import TransfermarktRefereesParser
from .persistence import atomic_json_dump, load_versioned_json

logger = logging.getLogger(__name__)
CACHE_VERSION = 2


class RefereesHelper:
    def __init__(
        self,
        context: ExecutionContext,
        http_client: HttpClient | None = None,
        parser: TransfermarktRefereesParser | None = None,
    ):
        self.context = context
        self.http_client = http_client or HttpClient()
        self.parser = parser or TransfermarktRefereesParser()
        self.season_division_matches: dict[str, dict[str, dict[str, list[Any]]]] = {}
        self.referee_names_to_id: dict[str, int] = {}
        self.current_referee_id = 1
        if context.enable_referees:
            self.load_values(context.referees_path)

    def getMatchRefereeAndResults(
        self, season: int, division: int, match_date: str, local_name: str, away_name: str
    ) -> tuple[str, int, str]:
        if not self.context.enable_referees:
            return "", -1, ""
        season_key = str(season)
        division_key = str(division)
        season_data = self.season_division_matches.setdefault(season_key, {})
        if division_key not in season_data:
            season_data[division_key] = self._scrape_season(season, division)
        cached = season_data[division_key].get(
            f"{match_date}-{local_name}-{away_name}", ("", -1, "")
        )
        return (str(cached[0]), int(cached[1]), str(cached[2]))

    def _referee_id(self, name: str) -> int:
        if name not in self.referee_names_to_id:
            self.referee_names_to_id[name] = self.current_referee_id
            self.current_referee_id += 1
        return self.referee_names_to_id[name]

    def _scrape_season(self, season: int, division: int) -> dict[str, list[Any]]:
        response = self.http_client.get(const.REFEREES_URL % (division, season))
        result = {}
        for name, href in self.parser.parse_referee_links(response.text):
            referee_id = self._referee_id(name)
            match_response = self.http_client.get(
                const.REFEREES_MATCHES_URL % (href, season, division)
            )
            for row in self.parser.parse_matches(match_response.text, name, referee_id):
                key = f"{row['date']}-{row['home_name']}-{row['away_name']}"
                result[key] = [name, referee_id, row.get("result", "")]
        return result

    def save_values(self, path: str | Path | None = None) -> None:
        path = path or self.context.referees_path
        atomic_json_dump(
            path,
            {"version": CACHE_VERSION, "cache": self.season_division_matches},
        )

    def load_values(self, path: str | Path | None = None) -> None:
        path = path or self.context.referees_path
        try:
            payload = load_versioned_json(
                path,
                cache_name="árbitros",
                current_version=CACHE_VERSION,
            )
            if payload is not None:
                self.season_division_matches = payload["cache"]
        except (OSError, ValueError, TypeError) as error:
            logger.warning("No se pudo cargar la caché de árbitros %s: %s", path, error)

    SAVE_REFEREES_VALUES = save_values
    _LOAD_REFEREES_VALUES = load_values
