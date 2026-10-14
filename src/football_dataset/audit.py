"""Auditoría offline de datasets de partidos y ML.

Uso:
    python -m src.football_dataset.audit --input data/dataset_ml.csv --format text
    python -m src.football_dataset.audit --input data/dataset_ml.csv --format json
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

EXPECTED_ML_METADATA = "# football_dataset_ml=1"
TARGET_VALUES = {"1", "X", "2"}


def read_csv(path: Path) -> tuple[str, list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as file:
        metadata = file.readline().rstrip("\r\n")
        reader = csv.DictReader(file, delimiter=";")
        return metadata, list(reader.fieldnames or []), list(reader)


def as_float(row: dict[str, str], column: str) -> float | None:
    try:
        return float(row[column])
    except (KeyError, TypeError, ValueError):
        return None


def audit_dataset(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    metadata, columns, rows = read_csv(source)
    issues: list[str] = []
    warnings: list[str] = []
    required = {"division", "temporada", "jornada", "resultado1X2"}
    missing = sorted(required - set(columns))
    if missing:
        issues.append(f"Faltan columnas obligatorias: {', '.join(missing)}")

    target_counts = Counter(row.get("resultado1X2", "") for row in rows)
    invalid_targets = sum(
        count for value, count in target_counts.items() if value not in TARGET_VALUES
    )
    if invalid_targets:
        issues.append(f"Hay {invalid_targets} filas con resultado1X2 invÃ¡lido o vacÃ­o")

    duplicate_key: Callable[[dict[str, str]], tuple[str, ...]] | None
    if "idPartido" in columns:

        def duplicate_key(row: dict[str, str]) -> tuple[str, ...]:
            return (
                row.get("division", ""),
                row.get("temporada", ""),
                row.get("jornada", ""),
                row.get("idPartido", ""),
            )

    elif {"localId", "visitanteId"}.issubset(columns):

        def duplicate_key(row: dict[str, str]) -> tuple[str, ...]:
            return (
                row.get("division", ""),
                row.get("temporada", ""),
                row.get("jornada", ""),
                row.get("localId", ""),
                row.get("visitanteId", ""),
            )

    else:
        duplicate_key = None

    if duplicate_key is not None:
        duplicates = Counter(duplicate_key(row) for row in rows)
        duplicate_count = sum(count - 1 for count in duplicates.values() if count > 1)
        if duplicate_count:
            issues.append(f"Hay {duplicate_count} filas duplicadas por clave de partido")
    else:
        duplicate_count = 0
        warnings.append("No se puede auditar duplicidad: faltan identificadores del partido")

    if {"localId", "visitanteId"}.issubset(columns):
        missing_teams = sum(1 for row in rows if not row.get("localId") or not row.get("visitanteId"))
        if missing_teams:
            issues.append(f"Hay {missing_teams} filas sin identidad local/visitante")
    else:
        warnings.append("El CSV no contiene localId/visitanteId para identificar el enfrentamiento")

    score_checks = 0
    inconsistent_scores = 0
    inconsistent_targets = 0
    opening_state_issues = 0
    monotonicity_issues = 0
    history_rows: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        division = row.get("division", "")
        season = row.get("temporada", "")
        try:
            round_number = int(row.get("jornada", ""))
        except ValueError:
            continue
        history_rows[(division, season, round_number)].append(row)
        if {"golesLocal", "golesVisitante", "golDiff"}.issubset(columns):
            try:
                home, away, diff = (
                    int(row["golesLocal"]),
                    int(row["golesVisitante"]),
                    int(row["golDiff"]),
                )
                score_checks += 1
                if diff != home - away:
                    inconsistent_scores += 1
            except (TypeError, ValueError):
                pass
        if "resultado1X2" in columns and {"golesLocal", "golesVisitante"}.issubset(columns):
            try:
                expected = (
                    "1"
                    if int(row["golesLocal"]) > int(row["golesVisitante"])
                    else "X"
                    if int(row["golesLocal"]) == int(row["golesVisitante"])
                    else "2"
                )
                if row["resultado1X2"] != expected:
                    inconsistent_targets += 1
            except (TypeError, ValueError):
                pass

    for (_division, _season, round_number), round_rows in history_rows.items():
        if round_number == 1:
            for row in round_rows:
                for column in (
                    "puntosLocal",
                    "puntosVisitante",
                    "golesafavorlocal",
                    "golesencontralocal",
                    "golesafavorvisitante",
                    "golesencontravisitante",
                    "rachaLocal",
                    "rachaVisitante",
                ):
                    if column in columns and as_float(row, column) not in {0.0, None}:
                        opening_state_issues += 1

    if {"localId", "visitanteId"}.issubset(columns):
        team_history: dict[tuple[str, str, str], list[tuple[int, dict[str, float | None]]]] = defaultdict(list)
        for row in rows:
            try:
                round_number = int(row.get("jornada", ""))
            except ValueError:
                continue
            key_base = (row.get("division", ""), row.get("temporada", ""))
            for team_column, stat_columns in (
                ("localId", ("puntosLocal", "golesafavorlocal", "golesencontralocal")),
                ("visitanteId", ("puntosVisitante", "golesafavorvisitante", "golesencontravisitante")),
            ):
                key = (*key_base, row.get(team_column, ""))
                current_values = {column: as_float(row, column) for column in stat_columns}
                previous_entries = [entry for entry in team_history[key] if entry[0] < round_number]
                if previous_entries:
                    previous = max(previous_entries, key=lambda entry: entry[0])[1]
                    for column, current in current_values.items():
                        previous_value = previous.get(column)
                        if (
                            current is not None
                            and previous_value is not None
                            and current < previous_value
                            and current >= 0
                            and previous_value >= 0
                        ):
                            monotonicity_issues += 1
                team_history[key].append((round_number, current_values))
    else:
        warnings.append("No se audita monotonÃ­a por equipo: faltan localId/visitanteId")

    if inconsistent_scores:
        issues.append(f"{inconsistent_scores}/{score_checks} diferencias de goles incoherentes")
    if inconsistent_targets:
        issues.append(f"{inconsistent_targets} etiquetas resultado1X2 incoherentes con el marcador")
    if opening_state_issues:
        issues.append(f"{opening_state_issues} valores acumulados no empiezan a cero en jornada 1")
    if monotonicity_issues:
        issues.append(f"{monotonicity_issues} acumulados disminuyen entre jornadas")

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        group_key = (row.get("division", ""), row.get("temporada", ""))
        try:
            groups[group_key].append(int(row.get("jornada", "")))
        except ValueError:
            issues.append(f"Jornada no numÃ©rica en {group_key}")

    season_report: dict[str, dict[str, Any]] = {}
    for group_key, rounds in sorted(groups.items()):
        name = f"division={group_key[0]};temporada={group_key[1]}"
        unique_rounds = sorted(set(rounds))
        gaps = (
            [
                number
                for number in range(unique_rounds[0], unique_rounds[-1] + 1)
                if number not in unique_rounds
            ]
            if unique_rounds
            else []
        )
        season_report[name] = {
            "rows": len(rounds),
            "rounds": len(unique_rounds),
            "min_round": unique_rounds[0] if unique_rounds else None,
            "max_round": unique_rounds[-1] if unique_rounds else None,
            "gaps": gaps,
        }
        if gaps:
            warnings.append(f"Jornadas ausentes en {name}: {gaps}")

    non_numeric = {
        "temporada",
        "resultado1X2",
        "matchDate",
        "arbitroName",
        "localName",
        "visitanteName",
        "formaLocal",
        "formaVisitante",
    }
    numeric_columns = [column for column in columns if column not in non_numeric]
    invalid_numeric: dict[str, int] = {}
    for column in numeric_columns:
        invalid = sum(1 for row in rows if as_float(row, column) is None)
        if invalid:
            invalid_numeric[column] = invalid
            warnings.append(f"{column}: {invalid} valores no numÃ©ricos")

    if "distanciaKm" in columns:
        missing_distance = sum(1 for row in rows if as_float(row, "distanciaKm") in {None, -1.0})
        if missing_distance:
            warnings.append(f"distanciaKm ausente/desconocida en {missing_distance} filas")

    expected_metadata = (
        EXPECTED_ML_METADATA if "idPartido" not in columns else "# football_dataset_schema=3"
    )
    if metadata != expected_metadata:
        warnings.append(f"Metadato detectado: {metadata!r}; se esperaba {expected_metadata!r}")

    return {
        "path": str(source),
        "ok": not issues,
        "rows": len(rows),
        "columns": len(columns),
        "metadata": metadata,
        "target_counts": dict(target_counts),
        "duplicate_rows": duplicate_count,
        "invalid_numeric": invalid_numeric,
        "seasons": season_report,
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita un CSV de dataset offline")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    report = audit_dataset(args.input)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {report['path']}")
        print(f"Filas: {report['rows']} | Columnas: {report['columns']}")
        print(f"Resultado 1X2: {report['target_counts']}")
        print(f"Duplicados: {report['duplicate_rows']}")
        print(f"Estado: {'OK' if report['ok'] else 'ERROR'}")
        for message in report["issues"]:
            print(f"ERROR: {message}")
        for message in report["warnings"]:
            print(f"AVISO: {message}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
