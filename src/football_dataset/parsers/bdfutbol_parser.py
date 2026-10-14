from __future__ import annotations

import json
import re
from datetime import datetime

from ..models import RawMatch, RawTeam
from .errors import ParserError


class BDFutbolParser:
    TEAM_RE = re.compile(r'SE\[\d+\]="(?P<data>.*?)";')
    MATCH_RE = re.compile(r"SP\[(?P<round>\d+)\]\.push\((?P<payload>\{.*?\})\);")

    def parse(self, html: str) -> tuple[list[RawTeam], list[RawMatch]]:
        if not html or "resultats" not in html:
            raise ParserError("No se encontró el bloque 'resultats' de BDFutbol")
        teams = self.parse_teams(html)
        matches = self.parse_matches(html)
        if not teams:
            raise ParserError("BDFutbol no contiene equipos (bloques SE[])")
        if not matches:
            raise ParserError("BDFutbol no contiene partidos (bloques SP[].push())")
        return teams, matches

    def parse_teams(self, html: str) -> list[RawTeam]:
        result = []
        for found in self.TEAM_RE.finditer(html):
            parts = found.group("data").split("|", 1)
            if len(parts) != 2:
                raise ParserError(f"Equipo BDFutbol inválido: {found.group('data')}")
            try:
                result.append(RawTeam(int(parts[0]), parts[1].strip()))
            except ValueError as error:
                raise ParserError(f"ID de equipo BDFutbol inválido: {parts[0]}") from error
        return result

    def parse_matches(self, html: str) -> list[RawMatch]:
        result = []
        for found in self.MATCH_RE.finditer(html):
            try:
                payload = json.loads(found.group("payload"))
                required = ("d", "a1", "a2", "g1", "g2")
                missing = [field for field in required if payload.get(field) is None]
                if missing:
                    raise ParserError(
                        f"Partido BDFutbol sin campos obligatorios: {', '.join(missing)}"
                    )
                parsed_date = datetime.strptime(payload["d"], "%d/%m/%Y").date()
                result.append(
                    RawMatch(
                        int(found.group("round")),
                        parsed_date,
                        int(payload["a1"]),
                        int(payload["a2"]),
                        int(payload["g1"]),
                        int(payload["g2"]),
                    )
                )
            except ParserError:
                raise
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise ParserError(f"Partido BDFutbol inválido: {found.group('payload')}") from error
        return result
