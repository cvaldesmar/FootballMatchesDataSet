import json

import pytest

from src.football_dataset.context import ExecutionContext
from src.football_dataset.MarketHelper import MarketHelper
from src.football_dataset.persistence import (
    CacheCorruptError,
    CacheVersionError,
    atomic_write_text,
    load_versioned_json,
)
from src.football_dataset.RefereesHelper import RefereesHelper


def test_atomic_write_replaces_destination_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "nested" / "cache.json"
    atomic_write_text(path, "first")
    atomic_write_text(path, "second")

    assert path.read_text(encoding="utf-8") == "second"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_versioned_json_rejects_corrupt_and_unknown_payloads(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(CacheCorruptError, match="corrupta"):
        load_versioned_json(path, cache_name="prueba", current_version=2)

    path.write_text(json.dumps({"version": 99, "cache": {}}), encoding="utf-8")
    with pytest.raises(CacheVersionError, match="no compatible"):
        load_versioned_json(path, cache_name="prueba", current_version=2)

    path.write_text(json.dumps({"version": 2}), encoding="utf-8")
    with pytest.raises(CacheCorruptError, match="campo 'cache'"):
        load_versioned_json(path, cache_name="prueba", current_version=2)


def test_versioned_json_applies_registered_migrations(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"version": 1, "cache": {"old": 1}}), encoding="utf-8")

    def migrate_v1(payload):
        return {"version": 2, "cache": {"new": payload["cache"]["old"]}}

    payload = load_versioned_json(
        path,
        cache_name="prueba",
        current_version=2,
        migrations={1: migrate_v1},
    )
    assert payload == {"version": 2, "cache": {"new": 1}}


def test_market_cache_unknown_version_is_not_silently_ignored(tmp_path):
    path = tmp_path / "market.json"
    path.write_text(json.dumps({"version": 999, "cache": {}}), encoding="utf-8")
    helper = MarketHelper(ExecutionContext(enable_market=False))

    with pytest.raises(CacheVersionError):
        helper.load_values(path)


def test_referee_cache_is_written_atomically_and_round_trips(tmp_path):
    path = tmp_path / "referees.json"
    context = ExecutionContext(enable_referees=False)
    helper = RefereesHelper(context)
    helper.season_division_matches = {"2021": {"1": {"key": ["Ref", 1, "2:1"]}}}
    helper.save_values(path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert payload["cache"] == helper.season_division_matches
    assert list(tmp_path.glob(".referees.json.*.tmp")) == []
