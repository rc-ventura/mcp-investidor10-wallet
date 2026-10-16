"""Unit tests for the long-term memory JSON store (schema v1, atomic writes, degraded mode)."""

import datetime
import glob
import json

import pytest

from memory_store import MemoryStore, MemoryUnavailableError


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "memory.json"))

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


# ----------------------------------------------------------------- domain operations


def test_wallet_goal_roundtrip(store):
    assert store.get_wallet_goal() is None
    goal = store.set_wallet_goal("Retirement: passive income of BRL 10k/month")
    assert goal["text"] == "Retirement: passive income of BRL 10k/month"
    assert goal["updated_at"]
    assert store.get_wallet_goal() == goal
    with pytest.raises(ValueError):
        store.set_wallet_goal("   ")


def test_save_thesis_normalizes_ticker_and_requires_text(store):
    thesis = store.save_thesis(" petr4 ", "High payout with contained capex")
    assert thesis["ticker"] == "PETR4"
    assert thesis["created_at"]
    assert thesis["updated_at"]
    assert thesis["text"] == "High payout with contained capex"
    with pytest.raises(ValueError):
        store.save_thesis("PETR4", "  ")
    with pytest.raises(ValueError):
        store.save_thesis(" ", "text")


def test_multiple_theses_same_ticker_keep_history(store):
    store.save_thesis("PETR4", "thesis v1")
    store.save_thesis("PETR4", "thesis v2")
    store.save_thesis("VALE3", "iron cycle")
    petr4_theses = store.get_theses("petr4")
    assert len(petr4_theses) == 2
    assert {t["text"] for t in petr4_theses} == {"thesis v1", "thesis v2"}
    assert len(store.get_theses()) == 3


def test_rules_save_and_list(store):
    rule = store.save_rule("Only buy with positive rating on Investidor10")
    assert rule["text"].startswith("Only buy")
    assert rule["created_at"]
    assert len(store.get_rules()) == 1
    with pytest.raises(ValueError):
        store.save_rule(" ")


def test_log_decision_defaults_to_pending(store):
    decision = store.log_decision(
        "recommendation", "Reduce concentration in PETR4 (15.2% vs 8% ideal)",
        ticker="petr4", rationale="Sector concentration risk",
    )
    assert decision["kind"] == "recommendation"
    assert decision["ticker"] == "PETR4"
    assert decision["outcome"] == "pending"
    assert decision["outcome_at"] is None
    assert decision["outcome_note"] is None
    assert decision["date"]
    with pytest.raises(ValueError):
        store.log_decision("wild-speculation", "buy everything")


def test_record_decision_outcome_transitions_and_stamps(store):
    decision = store.log_decision("recommendation", "Add to MXRF11 below ideal")
    updated = store.record_decision_outcome(decision["id"], "rejected", note="Not this month")
    assert updated["outcome"] == "rejected"
    assert updated["outcome_note"] == "Not this month"
    assert updated["outcome_at"]
    for invalid in ("pending", "maybe"):
        with pytest.raises(ValueError):
            store.record_decision_outcome(decision["id"], invalid)
    assert store.record_decision_outcome(999, "accepted") is None


def test_log_insight_dedupes_by_fingerprint(store):
    first = store.log_insight("concentration_alert", "PETR4:15.2>8.0", "PETR4 concentration alert shown")
    assert first["already_logged"] is False
    assert first["entry"]["fingerprint"] == "PETR4:15.2>8.0"

    duplicate = store.log_insight("concentration_alert", "PETR4:15.2>8.0", "would repeat the alert")
    assert duplicate["already_logged"] is True
    assert duplicate["existing"]["fingerprint"] == "PETR4:15.2>8.0"
    # SC-005: the duplicate insight was NOT appended.
    assert len(store.get_all("insights_log")) == 1


def test_session_digest_groups_theses_and_filters_pending(store):
    store.set_wallet_goal("Retirement")
    store.save_thesis("PETR4", "thesis A")
    store.save_thesis("vale3", "thesis B")
    store.save_rule("rule 1")
    pending = store.log_decision("recommendation", "Do X")
    done = store.log_decision("user_decision", "Did Y")
    store.record_decision_outcome(done["id"], "accepted")
    store.log_insight("concentration_alert", "PETR4:15>8", "alert")

    digest = store.session_digest()
    assert digest["wallet_goal"]["text"] == "Retirement"
    assert set(digest["theses"].keys()) == {"PETR4", "VALE3"}
    assert len(digest["rules"]) == 1
    assert [d["id"] for d in digest["pending_decisions"]] == [pending["id"]]
    assert digest["recent_insights"][-1]["fingerprint"] == "PETR4:15>8"


def test_domain_ops_raise_memory_unavailable_when_degraded(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("{corrupt", encoding="utf-8")
    degraded = MemoryStore(str(path))
    assert not degraded.available
    for op in (
        degraded.session_digest,
        lambda: degraded.save_thesis("PETR4", "x"),
        lambda: degraded.set_wallet_goal("x"),
        lambda: degraded.log_insight("k", "fp", "s"),
    ):
        with pytest.raises(MemoryUnavailableError):
            op()
