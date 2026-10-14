"""Validación de calidad antes de persistir el dataset."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    checked: int = 0
    issues: list[QualityIssue] = field(default_factory=list)
    max_errors: int | None = None

    @property
    def errors(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def valid(self) -> bool:
        return not self.errors or (
            self.max_errors is not None and len(self.errors) <= self.max_errors
        )

    @property
    def exceeds_error_threshold(self) -> bool:
        return self.max_errors is not None and len(self.errors) > self.max_errors

    def add(self, severity: str, code: str, message: str, **context: Any) -> None:
        self.issues.append(QualityIssue(severity, code, message, context))


class DatasetValidator:
    def validate_matches(
        self,
        matches: Iterable[Any],
        *,
        expected_teams: int | None = None,
        expected_matches: int | None = None,
        known_team_ids: Iterable[Any] | None = None,
        max_errors: int | None = 0,
    ) -> QualityReport:
        rows = list(matches)
        known_ids = set(known_team_ids) if known_team_ids is not None else None
        report = QualityReport(checked=len(rows), max_errors=max_errors)
        seen: set[tuple[Any, ...]] = set()
        teams: set[Any] = set()
        for index, match in enumerate(rows):
            home_id = self._get(match, "localId", "home_global_id", "home_season_id")
            away_id = self._get(match, "visitanteId", "away_global_id", "away_season_id")
            jornada = self._get(match, "jornada")
            match_date = self._get(match, "matchDate", "match_date")
            home_goals = self._get(match, "golesLocal", "home_goals")
            away_goals = self._get(match, "golesVisitante", "away_goals")
            key = (jornada, home_id, away_id)
            if key in seen:
                report.add("error", "duplicate_match", "Partido duplicado", row=index, key=key)
            seen.add(key)
            teams.update((home_id, away_id))
            if known_ids is not None:
                for side, team_id in (("local", home_id), ("visitante", away_id)):
                    if team_id not in known_ids:
                        report.add(
                            "error",
                            "unknown_team",
                            f"Equipo {side} desconocido",
                            row=index,
                            team_id=team_id,
                        )
            try:
                if int(jornada) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                report.add("error", "invalid_round", "Jornada inválida", row=index, value=jornada)
            try:
                if isinstance(match_date, datetime):
                    parsed_date = match_date.date()
                elif isinstance(match_date, date):
                    parsed_date = match_date
                else:
                    parsed_date = datetime.strptime(str(match_date), "%Y-%m-%d").date()
                if parsed_date.year < 1900:
                    raise ValueError
            except (TypeError, ValueError):
                report.add(
                    "error",
                    "invalid_date",
                    "Fecha inválida; se esperaba YYYY-MM-DD",
                    row=index,
                    value=match_date,
                )
            for field_name, goals in (("home_goals", home_goals), ("away_goals", away_goals)):
                try:
                    if int(goals) < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    report.add(
                        "error",
                        "invalid_score",
                        "Marcador inválido",
                        row=index,
                        field=field_name,
                        value=goals,
                    )
            goal_diff = self._get(match, "golDiff", "goal_diff")
            try:
                if int(goal_diff) != int(home_goals) - int(away_goals):
                    report.add(
                        "error",
                        "inconsistent_goal_diff",
                        "golDiff no coincide con el marcador",
                        row=index,
                    )
            except (TypeError, ValueError):
                pass
        if expected_teams is not None and len(teams) != expected_teams:
            report.add(
                "error",
                "unexpected_team_count",
                f"Se esperaban {expected_teams} equipos y hay {len(teams)}",
            )
        if expected_matches is not None and len(rows) != expected_matches:
            report.add(
                "error",
                "unexpected_match_count",
                f"Se esperaban {expected_matches} partidos y hay {len(rows)}",
            )
        return report

    @staticmethod
    def _get(item: Any, *names: str) -> Any:
        for name in names:
            if isinstance(item, dict) and name in item:
                return item[name]
            if hasattr(item, name):
                return getattr(item, name)
        return None
