from datetime import date

import pytest

from src.football_dataset.validation import DatasetValidator


def match(**overrides):
    value = {
        "jornada": 1,
        "localId": 1,
        "visitanteId": 2,
        "matchDate": "2021-09-12",
        "golesLocal": 2,
        "golesVisitante": 1,
        "golDiff": 1,
    }
    value.update(overrides)
    return value


def codes(report):
    return {issue.code for issue in report.issues}


def test_validator_detects_unknown_teams_round_date_and_scores():
    report = DatasetValidator().validate_matches(
        [match(jornada=0, visitanteId=99, matchDate="not-a-date", golesLocal=-1, golDiff=20)],
        known_team_ids={1, 2},
    )

    assert not report.valid
    assert codes(report) == {
        "unknown_team",
        "invalid_round",
        "invalid_date",
        "invalid_score",
        "inconsistent_goal_diff",
    }


def test_validator_detects_expected_counts_and_duplicates():
    row = match()
    report = DatasetValidator().validate_matches(
        [row, row],
        expected_teams=3,
        expected_matches=3,
    )

    assert not report.valid
    assert codes(report) == {"duplicate_match", "unexpected_team_count", "unexpected_match_count"}
    assert report.checked == 2


@pytest.mark.parametrize("value", [date(2021, 9, 12), "2021-09-12"])
def test_validator_accepts_iso_date_and_date_objects(value):
    report = DatasetValidator().validate_matches([match(matchDate=value)])
    assert report.valid
    assert not report.issues


def test_validator_max_errors_controls_validity_but_does_not_hide_issues():
    report = DatasetValidator().validate_matches(
        [match(jornada=0, golesLocal=-1)],
        max_errors=3,
    )

    assert len(report.errors) == 3
    assert report.valid
    assert not report.exceeds_error_threshold

    strict = DatasetValidator().validate_matches([match(jornada=0, golesLocal=-1)], max_errors=2)
    assert not strict.valid
    assert strict.exceeds_error_threshold


def test_validator_keeps_warnings_separate_from_errors():
    report = DatasetValidator().validate_matches([match()])
    report.add("warning", "sample_warning", "Advertencia de prueba")

    assert report.valid
    assert len(report.warnings) == 1
    assert not report.errors
