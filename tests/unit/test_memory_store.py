"""Unit tests for the long-term memory JSON store (schema v1, atomic writes, degraded mode)."""

import datetime
import glob
import json
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

from investidor10_wallet.memory_store import MemoryStore, MemoryUnavailableError


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
    entry = store.add(
        "insights_log", {"kind": "concentration_alert", "fingerprint": "PETR4:15.2>8.0"}
    )
    assert "created_at" in entry
    parsed = datetime.datetime.fromisoformat(entry["created_at"])
    assert parsed.utcoffset() is not None


def test_find_and_update_persist_changes(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    entry = store.add("theses", {"ticker": "PETR4", "text": "original"})
    assert store.find("theses", entry["id"])["text"] == "original"
    assert store.find("theses", 999) is None

    updated = store.update(
        "theses",
        entry["id"],
        {"text": "revised", "updated_at": "2026-10-10T12:00:00-03:00"},
    )
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
    future = {
        "version": 99,
        "wallet_goal": None,
        "theses": [],
        "rules": [],
        "decisions": [],
        "insights_log": [],
        "alerts": [],
    }
    path.write_text(json.dumps(future), encoding="utf-8")

    store = MemoryStore(str(path))
    assert not store.available
    with pytest.raises(MemoryUnavailableError):
        store.get_all("rules")
    # Valid JSON with an unknown version is kept as-is: no .broken- backup needed.
    assert glob.glob(str(tmp_path / "memory.json.broken-*")) == []
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 99


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"version": "1"},
        {"version": True},
        {
            "version": 1,
            "wallet_goal": None,
            "theses": {},
            "rules": [],
            "decisions": [],
            "insights_log": [],
            "alerts": [],
        },
        {
            "version": 1,
            "wallet_goal": None,
            "theses": [],
            "rules": [],
            "decisions": [],
            "insights_log": [],
            "alerts": [None],
        },
        {
            "version": 1,
            "wallet_goal": None,
            "theses": [],
            "rules": [],
            "decisions": [],
            "insights_log": [],
            "alerts": [{"id": "bad"}],
        },
        {
            "version": 1,
            "wallet_goal": None,
            "theses": [],
            "rules": [],
            "decisions": [],
            "insights_log": [],
            "alerts": [
                {
                    "id": 1,
                    "ticker": "PETR4",
                    "direction": "below",
                    "limit_price": 30,
                    "state": "active",
                },
                {
                    "id": 1,
                    "ticker": "VALE3",
                    "direction": "below",
                    "limit_price": 20,
                    "state": "active",
                },
            ],
        },
        {
            "version": 1,
            "wallet_goal": None,
            "theses": [],
            "rules": [],
            "decisions": [],
            "insights_log": [],
            "alerts": [{"ticker": "PETR4"}],
        },
    ],
)
def test_invalid_schema_degrades_and_preserves_file(tmp_path, data):
    path = tmp_path / "memory.json"
    path.write_text(json.dumps(data))
    store = MemoryStore(str(path))
    assert not store.available
    assert json.loads(path.read_text()) == data
    assert len(glob.glob(str(path) + ".broken-*")) == 1


def test_unreadable_file_degrades_without_crashing(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("private")
    with patch.object(MemoryStore, "_read_file", side_effect=PermissionError("denied")):
        store = MemoryStore(str(path))
    assert not store.available
    assert path.read_text() == "private"
    assert glob.glob(str(path) + ".broken-*") == []


def test_memory_deleted_while_running_is_not_recreated_empty(tmp_path, capsys):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.save_rule("máximo 10% por ativo")
    path.unlink()

    with pytest.raises(MemoryUnavailableError):
        store.get_rules()
    with pytest.raises(MemoryUnavailableError):
        store.save_rule("outra regra")
    assert not path.exists()
    assert capsys.readouterr().err.count("sumiu com o servidor rodando") == 1


def test_restored_memory_file_is_available_again(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.save_rule("r")
    content = path.read_text()
    path.unlink()
    with pytest.raises(MemoryUnavailableError):
        store.get_rules()

    path.write_text(content)

    assert [rule["text"] for rule in store.get_rules()] == ["r"]


def test_a_restarted_server_starts_an_empty_memory_when_the_file_is_gone(tmp_path):
    path = tmp_path / "memory.json"
    MemoryStore(str(path)).save_rule("r")
    path.unlink()
    assert MemoryStore(str(path)).get_rules() == []


def test_transient_read_error_degrades_without_a_corruption_backup(
    tmp_path, monkeypatch
):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.save_rule("r")

    def denied(*args, **kwargs):
        raise PermissionError("locked by antivirus")

    monkeypatch.setattr(MemoryStore, "_read_file", denied)
    with pytest.raises(MemoryUnavailableError):
        store.get_rules()
    assert glob.glob(str(path) + ".broken-*") == []

    monkeypatch.undo()
    assert [rule["text"] for rule in store.get_rules()] == ["r"]


def test_read_only_store_never_writes_a_corruption_backup(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.read_only = True
    path.write_text("{broken")

    with pytest.raises(MemoryUnavailableError):
        store.get_rules()
    assert glob.glob(str(path) + ".broken-*") == []


def test_write_is_fsynced_before_the_atomic_rename(store, monkeypatch):
    calls = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(fd):
        calls.append("fsync")
        real_fsync(fd)

    def replace(source, destination):
        calls.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "replace", replace)
    store.save_rule("r")
    assert calls == ["fsync", "replace"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlinks")
def test_memory_file_swapped_for_a_symlink_is_never_followed(tmp_path, capsys):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.save_rule("r")
    secret = tmp_path / "secret.txt"
    secret.write_text('{"version": 1}')
    path.unlink()
    path.symlink_to(secret)

    with pytest.raises(MemoryUnavailableError):
        store.get_rules()
    with pytest.raises(MemoryUnavailableError):
        store.save_rule("outra")

    assert path.is_symlink()  # never replaced or detached
    assert secret.read_text() == '{"version": 1}'
    assert glob.glob(str(path) + ".broken-*") == []
    assert capsys.readouterr().err.count("link simbólico") == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlinks")
def test_symlinked_memory_path_is_unavailable_from_the_start(tmp_path):
    real = tmp_path / "real.json"
    MemoryStore(str(real)).save_rule("r")
    link = tmp_path / "memory.json"
    link.symlink_to(real)

    store = MemoryStore(str(link))

    assert not store.available
    assert link.is_symlink()


def test_first_run_save_failure_degrades(tmp_path):
    store = MemoryStore(str(tmp_path / "missing" / "memory.json"))
    assert not store.available
    with pytest.raises(MemoryUnavailableError):
        store.get_wallet_goal()


def test_save_failure_returns_memory_unavailable_without_overwriting_original(
    store, tmp_path, monkeypatch
):
    original = (tmp_path / "memory.json").read_text()
    monkeypatch.setattr(
        "investidor10_wallet.memory_store.os.replace",
        lambda *args: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(MemoryUnavailableError):
        store.set_wallet_goal("Retirement")
    assert not store.available
    assert (tmp_path / "memory.json").read_text() == original
    assert list(tmp_path.glob(".memory-*")) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlink creation")
def test_save_does_not_follow_preexisting_tmp_symlink(store, tmp_path):
    victim = tmp_path / "victim"
    victim.write_text("untouched")
    (tmp_path / "memory.json.tmp").symlink_to(victim)
    store.save()
    assert victim.read_text() == "untouched"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: file mode bits")
def test_corrupt_backup_is_created_with_private_permissions(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("{broken")
    MemoryStore(str(path))
    backups = glob.glob(str(path) + ".broken-*")
    assert len(backups) == 1
    assert os.stat(backups[0]).st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "content",
    [
        '{"version": NaN}',
        '{"version": 1, "wallet_goal": null, "theses": [], "rules": [], "decisions": [], "insights_log": [], "alerts": [{"limit_price": Infinity}]}',
    ],
)
def test_nonstandard_numeric_constants_degrade(tmp_path, content):
    path = tmp_path / "memory.json"
    path.write_text(content)
    assert not MemoryStore(str(path)).available
    assert path.read_text() == content


@pytest.mark.parametrize(
    "content",
    [
        "directory",
        "missing_parent",
        "invalid_json",
        '{"version": "1"}',
        '{"version": 1}',
        "{}",
        '{"version": 2}',
    ],
)
def test_import_server_degrades_on_unusable_memory(tmp_path, content):
    path = tmp_path / "memory.json"
    if content == "directory":
        path.mkdir()
    elif content == "missing_parent":
        path = tmp_path / "missing" / "memory.json"
    else:
        path.write_text("{corrupt" if content == "invalid_json" else content)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from investidor10_wallet import server; assert not server.memory.available",
        ],
        check=False,
        env={
            **os.environ,
            "WALLET_MEMORY_PATH": str(path),
            "PYTHONPATH": os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "src")
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


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
        "recommendation",
        "Reduce concentration in PETR4 (15.2% vs 8% ideal)",
        ticker="petr4",
        rationale="Sector concentration risk",
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
    updated = store.record_decision_outcome(
        decision["id"], "rejected", note="Not this month"
    )
    assert updated["outcome"] == "rejected"
    assert updated["outcome_note"] == "Not this month"
    assert updated["outcome_at"]
    for invalid in ("pending", "maybe"):
        with pytest.raises(ValueError):
            store.record_decision_outcome(decision["id"], invalid)
    assert store.record_decision_outcome(999, "accepted") is None


def test_log_insight_dedupes_by_fingerprint(store):
    first = store.log_insight(
        "concentration_alert", "PETR4:15.2>8.0", "PETR4 concentration alert shown"
    )
    assert first["already_logged"] is False
    assert first["entry"]["fingerprint"] == "PETR4:15.2>8.0"

    duplicate = store.log_insight(
        "concentration_alert", "PETR4:15.2>8.0", "would repeat the alert"
    )
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
