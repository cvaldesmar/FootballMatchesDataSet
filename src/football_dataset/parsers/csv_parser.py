from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .errors import ParserError


class BDFutbolCSVParser:
    REQUIRED = {
        "division",
        "temporada",
        "jornada",
        "matchDate",
        "localName",
        "localId",
        "visitanteName",
        "visitanteId",
        "golesLocal",
        "golesVisitante",
        "golDiff",
    }

    def parse(self, path: str | Path, division: int, temporada: str) -> list[dict[str, str]]:
        try:
            with open(path, encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file, delimiter=";")
                fields = set(reader.fieldnames or ())
                missing = self.REQUIRED - fields
                if missing:
                    raise ParserError(
                        f"CSV sin columnas obligatorias: {', '.join(sorted(missing))}"
                    )
                rows = [
                    row
                    for row in reader
                    if int(row["division"]) == division and row["temporada"] == temporada
                ]
        except (OSError, csv.Error, ValueError) as error:
            raise ParserError(f"No se pudo leer el CSV {path}: {error}") from error
        for row in rows:
            try:
                datetime.strptime(row["matchDate"], "%Y-%m-%d")
                if (
                    int(row["jornada"]) <= 0
                    or int(row["golesLocal"]) < 0
                    or int(row["golesVisitante"]) < 0
                ):
                    raise ValueError
                if int(row["golDiff"]) != int(row["golesLocal"]) - int(row["golesVisitante"]):
                    raise ValueError("golDiff inconsistente")
            except ValueError as error:
                raise ParserError(
                    f"Fila CSV inválida: {row.get('idPartido', '<sin id>')}: {error}"
                ) from error
        return rows
