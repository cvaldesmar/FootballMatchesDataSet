"""Generación offline de un dataset simplificado para pronóstico 1X2."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable
from pathlib import Path

from .dataset_io import HEADERS, SCHEMA_METADATA_PREFIX

ML_METADATA_PREFIX = "# football_dataset_ml=1"
DROP_COLUMNS = {
    "idPartido",
    "localName",
    "visitanteName",
    "localId",
    "visitanteId",
    "arbitroName",
    "arbitroId",
    "matchDate",
}
ML_COLUMNS = [
    "division",
    "temporada",
    "jornada",
    "localId",
    "visitanteId",
    "diferenciaPuntos",
    "diferenciaPosicion",
    "diferenciaGolesNeta",
    "rachaLocal",
    "rachaVisitante",
    "h2hMatches",
    "h2hBalance",
    "campeonDecidido",
    "descensoConfirmadoLocal",
    "descensoConfirmadoVisitante",
    "presionLocal",
    "presionVisitante",
    "rivalidad",
    "distanciaKm",
    "diferenciaValorMercado",
    "ratioValorMercado",
    "resultado1X2",
]


def _number(row: dict[str, str], column: str) -> float:
    try:
        return float(row.get(column, ""))
    except (TypeError, ValueError):
        return -1.0


def transform_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Crea features derivadas usando solo snapshots previos ya persistidos.

    Las diferencias enfrentan local y visitante; ``ventajaLocal`` compara
    puntos por jornada usando el máximo teórico de tres puntos por partido.
    """
    transformed: list[dict[str, str]] = []
    for source in rows:
        row = {column: source.get(column, "") for column in ML_COLUMNS if column in source}
        local_market = _number(source, "localMarketValue")
        away_market = _number(source, "visitanteMarketValue")
        local_goal_balance = _number(source, "golesafavorlocal") - _number(
            source, "golesencontralocal"
        )
        away_goal_balance = _number(source, "golesafavorvisitante") - _number(
            source, "golesencontravisitante"
        )
        row["diferenciaValorMercado"] = str(local_market - away_market)
        row["ratioValorMercado"] = str(
            local_market / away_market if away_market > 0 and local_market >= 0 else -1.0
        )
        row["diferenciaPosicion"] = str(
            _number(source, "posicionVisitante") - _number(source, "posicionLocal")
        )
        row["diferenciaGolesNeta"] = str(local_goal_balance - away_goal_balance)
        row["h2hBalance"] = str(_number(source, "h2hLocalWins") - _number(source, "h2hAwayWins"))
        row["campeonDecidido"] = str(1 if _number(source, "campeonId") >= 0 else 0)
        transformed.append({column: row.get(column, "") for column in ML_COLUMNS})
    return transformed


def _read_source(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    with source.open(encoding="utf-8", newline="") as file:
        if file.readline().rstrip("\r\n") != SCHEMA_METADATA_PREFIX:
            raise ValueError(f"CSV sin esquema v3: {source}")
        reader = csv.DictReader(file, delimiter=";")
        if reader.fieldnames != HEADERS:
            raise ValueError(f"Cabecera CSV incompatible: {source}")
        return list(reader)


def build_ml_features(input_path: str | Path, output_path: str | Path) -> int:
    """Genera el artefacto ML sin modificar el dataset fuente."""
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    if source == destination:
        raise ValueError("El dataset ML debe escribirse en una ruta distinta al dataset fuente")
    rows = transform_rows(_read_source(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        file.write(ML_METADATA_PREFIX + "\n")
        writer = csv.DictWriter(file, fieldnames=ML_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera features simplificadas para ML")
    parser.add_argument("--input", required=True, help="CSV v3 fuente")
    parser.add_argument("--output", required=True, help="CSV ML derivado")
    args = parser.parse_args()
    print(f"Filas transformadas: {build_ml_features(args.input, args.output)}")


if __name__ == "__main__":
    main()
