"""Unit tests for the long-term memory JSON store (schema v1, atomic writes, degraded mode)."""

import datetime
import glob
import json

import pytest

from memory_store import MemoryStore, MemoryUnavailableError

SCHEMA_COLLECTIONS = ("theses", "rules", "decisions", "insights_log", "alerts")


def test_creates_empty_store_on_first_load(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    assert path.exists()
    assert store.available
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    for key in SCHEMA_COLLECTIONS:
        assert data[key] == []
    assert data["wallet_goal"] is None


def test_add_assigns_monotonic_ids_per_collection_and_persists(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    first = store.add("theses", {"ticker": "PETR4", "text": "high payout"})
    second = store.add("theses", {"ticker": "VALE3", "text": "iron cycle"})
    rule = store.add("rules", {"text": "only buy with positive rating"})
    assert first["id"] == 1
    assert second["id"] == 2
    # IDs are monotonic per collection, not global.
    assert rule["id"] == 1

    # Data survives a restart (a new store instance over the same file).
    reloaded = MemoryStore(str(path))
    assert len(reloaded.get_all("theses")) == 2
    assert len(reloaded.get_all("rules")) == 1


def test_add_stamps_local_timezone_iso_timestamp(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.json"))
    entry = store.add("insights_log", {"kind": "concentration_alert", "fingerprint": "PETR4:15.2>8.0"})
    assert "created_at" in entry
    parsed = datetime.datetime.fromisoformat(entry["created_at"])
    assert parsed.utcoffset() is not None


def test_find_and_update_persist_changes(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    entry = store.add("theses", {"ticker": "PETR4", "text": "original"})
    assert store.find("theses", entry["id"])["text"] == "original"
    assert store.find("theses", 999) is None

    updated = store.update("theses", entry["id"], {"text": "revised", "updated_at": "2026-10-10T12:00:00-03:00"})
    assert updated["text"] == "revised"
    assert store.find("theses", entry["id"])["text"] == "revised"

    reloaded = MemoryStore(str(path))
    assert reloaded.find("theses", entry["id"])["text"] == "revised"


def test_save_is_atomic_no_tmp_file_left_behind(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.add("rules", {"text": "rule"})
    store.save()
    assert not (tmp_path / "memory.json.tmp").exists()
    assert path.exists()


def test_corrupted_file_degrades_without_crash_and_creates_backup(tmp_path):
    path = tmp_path / "memory.json"
    corrupt_content = "{ this is not valid json"
    path.write_text(corrupt_content, encoding="utf-8")

    store = MemoryStore(str(path))
    assert not store.available

    # Reads and writes fail with a structured error, never with a crash.
    with pytest.raises(MemoryUnavailableError):
        store.get_all("theses")
    with pytest.raises(MemoryUnavailableError):
        store.add("rules", {"text": "x"})

    # The corrupt original is preserved under a .broken-<timestamp> backup.
    backups = glob.glob(str(tmp_path / "memory.json.broken-*"))
    assert len(backups) == 1
    with open(backups[0], encoding="utf-8") as f:
        assert f.read() == corrupt_content
    # The original file is left untouched (not overwritten, not deleted).
    assert path.read_text(encoding="utf-8") == corrupt_content


def test_unknown_future_version_degrades_without_backup(tmp_path):
    path = tmp_path / "memory.json"
    future = {"version": 99, "wallet_goal": None, "theses": [], "rules": [], "decisions": [], "insights_log": [], "alerts": []}
    path.write_text(json.dumps(future), encoding="utf-8")

    store = MemoryStore(str(path))
    assert not store.available
    with pytest.raises(MemoryUnavailableError):
        store.get_all("rules")
    # Valid JSON with an unknown version is kept as-is: no .broken- backup needed.
    assert glob.glob(str(tmp_path / "memory.json.broken-*")) == []
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 99
