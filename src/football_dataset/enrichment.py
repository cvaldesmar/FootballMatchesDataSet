"""Descarga de cachés y enriquecimiento offline de datasets históricos."""

from __future__ import annotations

import argparse
import csv
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .Const import NAMES_TO_TRANSFERMARKT_NAMES
from .context import ExecutionContext
from .dataset_io import HEADERS, SCHEMA_METADATA_PREFIX, SCHEMA_VERSION
from .http_client import HttpError
from .MarketHelper import CACHE_VERSION as MARKET_CACHE_VERSION
from .MarketHelper import MarketHelper
from .persistence import atomic_json_dump, atomic_write_text, load_versioned_json
from .RefereesHelper import CACHE_VERSION as REFEREE_CACHE_VERSION
from .RefereesHelper import RefereesHelper
from .UtilsAndGlobals import get_travel_distance_km

logger = logging.getLogger(__name__)

SCHEMA_V2_HEADERS = [header for header in HEADERS if header != "resultado1X2"]
LEGACY_HEADERS = [header for header in HEADERS if header != "distanciaKm"]
SCHEMA_V1_HEADERS = [header for header in LEGACY_HEADERS if header != "resultado1X2"]


def _read_dataset_rows(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Lee un CSV v1/v2, aceptando v1 con o sin línea de metadato."""
    source = Path(path)
    with source.open(encoding="utf-8", newline="") as file:
        first_line = file.readline().rstrip("\r\n")
        if first_line.startswith("# football_dataset_schema="):
            try:
                version = int(first_line.rsplit("=", 1)[1])
            except ValueError as error:
                raise ValueError(f"Metadato de esquema inválido: {first_line!r}") from error
        else:
            version = 1
            file.seek(0)
        reader = csv.DictReader(file, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        if fieldnames in (LEGACY_HEADERS, SCHEMA_V1_HEADERS):
            return fieldnames, list(reader)
        if fieldnames == SCHEMA_V2_HEADERS:
            return fieldnames, list(reader)
        if version == SCHEMA_VERSION and fieldnames == HEADERS:
            return fieldnames, list(reader)
        raise ValueError(f"Cabecera CSV incompatible con el esquema {version}: {path}")


def migrate_csv_schema(source: str | Path, output_path: str | Path | None = None) -> int:
    """Migra un CSV v1/v2 a esquema v3 offline.

    La publicación usa escritura atómica y conserva todas las columnas de negocio,
    incluidos los enriquecimientos de mercado y árbitros.
    """
    source_path = Path(source)
    destination_path = Path(output_path) if output_path is not None else source_path
    _, rows = _read_dataset_rows(source_path)
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=HEADERS, delimiter=";")
    writer.writeheader()
    for row in rows:
        if not row.get("distanciaKm"):
            row["distanciaKm"] = str(get_travel_distance_km(row["localName"], row["visitanteName"]))
        try:
            home_goals, away_goals = int(row["golesLocal"]), int(row["golesVisitante"])
            row["resultado1X2"] = (
                "1" if home_goals > away_goals else "X" if home_goals == away_goals else "2"
            )
        except (KeyError, TypeError, ValueError):
            row["resultado1X2"] = ""
        writer.writerow(row)
    atomic_write_text(
        destination_path,
        SCHEMA_METADATA_PREFIX + "\n" + buffer.getvalue().rstrip("\r\n") + "\n",
    )
    return len(rows)


# Compatibilidad con el nombre usado por la CLI y por integraciones existentes.
migrate_dataset_csv = migrate_csv_schema


def _migrate_market_v2_to_v3(payload: dict[str, Any]) -> dict[str, Any]:
    """Convierte división→fecha→equipos en equipo→fecha→valor."""
    result: dict[str, dict[str, float]] = {}
    for division_data in payload.get("cache", {}).values():
        for day, values in division_data.items():
            for team, value in values.items():
                result.setdefault(team, {})[day] = float(value)
    return {"version": 3, "cache": result}


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    _, rows = _read_dataset_rows(path)
    for row in rows:
        row.setdefault("distanciaKm", "")
    return rows


def _clean(value: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return " ".join(
        word
        for word in text.replace("-", " ").split()
        if word not in {"fc", "cf", "ud", "rcd", "cd", "real", "club"}
    )


def _market_value(values: dict[str, float], team_name: str) -> float:
    mapped = NAMES_TO_TRANSFERMARKT_NAMES.get(team_name, team_name)
    candidates = [str(value) for value in mapped] if isinstance(mapped, list) else [str(mapped)]
    if team_name not in candidates:
        candidates.append(team_name)
    for candidate in candidates:
        if candidate in values:
            return float(values[candidate])
    for candidate in candidates:
        clean = _clean(candidate)
        for name, value in values.items():
            other = _clean(name)
            if clean == other or clean in other or other in clean:
                return float(value)
    return -1.0


def _build_market_index(market_cache: dict[str, Any]) -> dict[str, list[tuple[date, float]]]:
    return {
        team: sorted(
            [
                (datetime.strptime(day, "%Y-%m-%d").date(), float(value))
                for day, value in dates.items()
            ],
            key=lambda item: item[0],
        )
        for team, dates in market_cache.items()
    }


def _cache_market_value(
    market_index: dict[str, list[tuple[date, float]]],
    _division: int,
    match_date: date,
    team_name: str,
) -> float:
    names = [team_name]
    mapped = NAMES_TO_TRANSFERMARKT_NAMES.get(team_name, team_name)
    names.extend(
        [str(value) for value in mapped] if isinstance(mapped, list) else [str(mapped)]
    )
    candidates = [
        item for name in names for item in market_index.get(name, []) if item[0] <= match_date
    ]
    return max(candidates, key=lambda item: item[0])[1] if candidates else -1.0


def _referee_value(referee_cache: dict[str, Any], row: dict[str, str]) -> tuple[str, str]:
    season = str(row["temporada"].split("-")[0])
    division = str(row["division"])
    entries = referee_cache.get(season, {}).get(division, {})
    target_date = row["matchDate"]
    home = row["localName"]
    away = row["visitanteName"]
    exact = entries.get(f"{target_date}-{home}-{away}")
    if exact:
        return str(exact[0]), str(exact[1])
    home_clean, away_clean = _clean(home), _clean(away)
    for key, value in entries.items():
        parts = key.split("-", 1)
        if len(parts) != 2 or parts[0] != target_date:
            continue
        teams = parts[1].split("-", 1)
        if len(teams) == 2 and _clean(teams[0]) == home_clean and _clean(teams[1]) == away_clean:
            return str(value[0]), str(value[1])
    return "", "-1"


def enrich_csv(
    source: str | Path,
    destination: str | Path,
    market_cache_path: str | Path,
    referees_cache_path: str | Path,
) -> int:
    """Crea un CSV enriquecido sin realizar peticiones HTTP."""
    rows = _read_rows(source)
    market_payload = load_versioned_json(
        market_cache_path,
        cache_name="mercado",
        current_version=MARKET_CACHE_VERSION,
        migrations={2: _migrate_market_v2_to_v3},
    )
    referee_payload = load_versioned_json(
        referees_cache_path, cache_name="árbitros", current_version=REFEREE_CACHE_VERSION
    )
    if market_payload is None or referee_payload is None:
        raise FileNotFoundError("Faltan una o ambas cachés necesarias para enriquecer offline")
    market_index = _build_market_index(market_payload["cache"])

    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        file.write(SCHEMA_METADATA_PREFIX + "\n")
        writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter=";")
        writer.writeheader()
        for row in rows:
            match_date = datetime.strptime(row["matchDate"], "%Y-%m-%d").date()
            row["localMarketValue"] = str(
                _cache_market_value(
                    market_index, int(row["division"]), match_date, row["localName"]
                )
            )
            row["visitanteMarketValue"] = str(
                _cache_market_value(
                    market_index, int(row["division"]), match_date, row["visitanteName"]
                )
            )
            # Mantener la feature calculada al enriquecer: los CSV antiguos pueden
            # no traerla, en cuyo caso se aplica la convención de ausencia.
            row["distanciaKm"] = row.get("distanciaKm") or "-1"
            referee_name, referee_id = _referee_value(referee_payload["cache"], row)
            row["arbitroName"] = referee_name
            row["arbitroId"] = referee_id
            writer.writerow(row)
    return len(rows)


def seed_caches_from_dataset(
    source: str | Path,
    market_cache_path: str | Path,
    referees_cache_path: str | Path,
) -> tuple[int, int]:
    """Extrae del CSV los enriquecimientos que ya estén presentes, sin red."""
    rows = _read_rows(source)
    market_cache: dict[str, dict[str, dict[str, float]]] = {}
    referee_cache: dict[str, dict[str, dict[str, list[object]]]] = {}
    market_entries = referee_entries = 0
    for row in rows:
        division = row["division"]
        day = row["matchDate"]
        market_values = market_cache.setdefault(division, {}).setdefault(day, {})
        for team_field, value_field in (
            ("localName", "localMarketValue"),
            ("visitanteName", "visitanteMarketValue"),
        ):
            try:
                value = float(row[value_field])
            except (TypeError, ValueError):
                continue
            if value >= 0:
                if row[team_field] not in market_values:
                    market_entries += 1
                market_values[row[team_field]] = value
        try:
            referee_id = int(row["arbitroId"])
        except (TypeError, ValueError):
            referee_id = -1
        if row["arbitroName"] and referee_id >= 0:
            season = row["temporada"].split("-")[0]
            key = f"{day}-{row['localName']}-{row['visitanteName']}"
            entries = referee_cache.setdefault(season, {}).setdefault(division, {})
            if key not in entries:
                referee_entries += 1
            entries[key] = [row["arbitroName"], referee_id, ""]
    team_market_cache: dict[str, dict[str, float]] = {}
    for division_data in market_cache.values():
        for day, values in division_data.items():
            for team, value in values.items():
                team_market_cache.setdefault(team, {})[day] = value
    atomic_json_dump(
        market_cache_path,
        {"version": MARKET_CACHE_VERSION, "cache": team_market_cache},
    )
    atomic_json_dump(
        referees_cache_path,
        {"version": REFEREE_CACHE_VERSION, "cache": referee_cache},
    )
    return market_entries, referee_entries


def download_caches(
    source: str | Path,
    market_cache_path: str | Path,
    referees_cache_path: str | Path,
    *,
    download_market: bool = True,
    download_referees: bool = True,
) -> None:
    """Descarga cachés usando el CSV histórico, sin volver a descargar BDFutbol.

    Las cachés se guardan después de cada división/temporada para poder reanudar
    tras un bloqueo de Transfermarkt sin perder lo ya descargado.
    """
    rows = _read_rows(source)
    context = ExecutionContext(
        source="file",
        input_path=str(source),
        enable_market=True,
        enable_referees=True,
        market_path=str(market_cache_path),
        referees_path=str(referees_cache_path),
    )
    market = MarketHelper(context)
    referees = RefereesHelper(context)
    market_groups: dict[int, list[dict[str, str]]] = {}
    referee_groups: dict[tuple[int, int], list[dict[str, str]]] = {}
    for row in rows:
        division = int(row["division"])
        season = int(row["temporada"].split("-")[0])
        market_groups.setdefault(division, []).append(row)
        referee_groups.setdefault((season, division), []).append(row)

    if download_market:
        for division, _division_rows in sorted(market_groups.items()):
            try:
                market.ensure_division_dates(division)
                market_days = sorted(market.market_info.get(division, {}))
                for index, market_day in enumerate(market_days, start=1):
                    if market.market_info[division].get(market_day):
                        continue
                    market.market_info[division][market_day] = market.scrape_team_values(
                        division, market_day
                    )
                    market.save_values(market_cache_path)
                    if index % 25 == 0:
                        logger.info(
                            "Mercado descargado: división %s, %d/%d fechas",
                            division,
                            index,
                            len(market_days),
                        )
                market.save_values(market_cache_path)
            except HttpError as error:
                market.save_values(market_cache_path)
                raise RuntimeError(
                    f"Transfermarkt bloqueó la caché de mercado en división {division}; "
                    f"se ha guardado el progreso en {market_cache_path}: {error}"
                ) from error

    if download_referees:
        for (season, division), season_rows in sorted(referee_groups.items()):
            if (
                str(season) in referees.season_division_matches
                and str(division) in referees.season_division_matches[str(season)]
            ):
                continue
            try:
                for row in season_rows:
                    referees.getMatchRefereeAndResults(
                        season, division, row["matchDate"], row["localName"], row["visitanteName"]
                    )
                referees.save_values(referees_cache_path)
            except HttpError as error:
                referees.save_values(referees_cache_path)
                raise RuntimeError(
                    f"Transfermarkt bloqueó la caché de árbitros en {season}/{division}; "
                    f"se ha guardado el progreso en {referees_cache_path}: {error}"
                ) from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Cachés y enriquecimiento offline del dataset")
    parser.add_argument("--input", required=True, help="CSV histórico con esquema versionado")
    parser.add_argument("--market-cache")
    parser.add_argument("--referees-cache")
    parser.add_argument("--migrate-output", help="Destino del CSV migrado a esquema 2")
    parser.add_argument(
        "--migrate-in-place", action="store_true", help="Migra --input reemplazándolo atómicamente"
    )
    parser.add_argument("--download-caches", action="store_true")
    parser.add_argument("--download-market", action="store_true")
    parser.add_argument("--download-referees", action="store_true")
    parser.add_argument(
        "--seed-caches",
        action="store_true",
        help="Extrae del CSV los valores de mercado y árbitros ya disponibles, sin red",
    )
    parser.add_argument("--enrich-output", help="CSV enriquecido de salida")
    args = parser.parse_args()
    if args.migrate_output or args.migrate_in_place:
        destination = args.input if args.migrate_in_place else args.migrate_output
        print(f"Filas migradas: {migrate_dataset_csv(args.input, destination)}")
        return
    if args.market_cache is None or args.referees_cache is None:
        parser.error("--market-cache y --referees-cache son obligatorios salvo al migrar")
    if args.seed_caches:
        market_count, referee_count = seed_caches_from_dataset(
            args.input, args.market_cache, args.referees_cache
        )
        print(f"Entradas de mercado guardadas: {market_count}")
        print(f"Entradas de árbitros guardadas: {referee_count}")
    if args.download_caches or args.download_market or args.download_referees:
        only_market = args.download_market and not args.download_referees
        only_referees = args.download_referees and not args.download_market
        download_caches(
            args.input,
            args.market_cache,
            args.referees_cache,
            download_market=not only_referees,
            download_referees=not only_market,
        )
    if args.enrich_output:
        count = enrich_csv(args.input, args.enrich_output, args.market_cache, args.referees_cache)
        print(f"Filas enriquecidas: {count}")


if __name__ == "__main__":
    main()
