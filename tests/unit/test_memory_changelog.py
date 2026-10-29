import json
import os
import sys

import pytest

from investidor10_wallet import bootstrap
from investidor10_wallet.memory_store import MemoryStore, MemoryUnavailableError

OPS = {"create", "update", "set", "trigger"}
COLLECTIONS = {"theses", "rules", "decisions", "insights_log", "alerts", "wallet_goal"}


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "memory.json")


def _log(path):
    with open(f"{path}.log", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.mark.parametrize(
    "collection,write",
    [
        ("rules", lambda s: s.save_rule("máximo 10% por ativo")),
        ("theses", lambda s: s.save_thesis("PETR4", "geração de caixa")),
        ("decisions", lambda s: s.log_decision("user_decision", "comprar")),
        ("alerts", lambda s: s.create_price_alert("PETR4", "below", 30.0)),
        ("insights_log", lambda s: s.log_insight("k", "fp", "resumo")),
    ],
)
def test_create_logs_one_line_without_before(path, collection, write):
    store = MemoryStore(path)
    entry = write(store)
    entry = entry.get("entry", entry)

    lines = _log(path)
    assert len(lines) == 1
    assert lines[0]["op"] == "create"
    assert lines[0]["collection"] == collection
    assert lines[0]["id"] == entry["id"]
    assert lines[0]["before"] is None
    assert lines[0]["after"] == entry


def test_update_logs_previous_and_new_state(path):
    store = MemoryStore(path)
    thesis = store.save_thesis("PETR4", "texto antigo")
    store.update("theses", thesis["id"], {"text": "texto novo"})

    lines = _log(path)
    assert [line["op"] for line in lines] == ["create", "update"]
    assert lines[1]["before"]["text"] == "texto antigo"
    assert lines[1]["after"]["text"] == "texto novo"
    assert lines[1]["id"] == thesis["id"]


def test_decision_outcome_and_alert_cancel_are_logged_as_updates(path):
    store = MemoryStore(path)
    decision = store.log_decision("recommendation", "vender")
    alert = store.create_price_alert("PETR4", "above", 50.0)
    store.record_decision_outcome(decision["id"], "rejected", "caro")
    store.cancel_price_alert(alert["id"])

    updates = [line for line in _log(path) if line["op"] == "update"]
    assert [u["collection"] for u in updates] == ["decisions", "alerts"]
    assert updates[0]["after"]["outcome"] == "rejected"
    assert updates[1]["after"]["state"] == "cancelled"
    assert updates[0]["before"]["outcome"] == "pending"
    assert updates[1]["before"]["state"] == "active"


def test_wallet_goal_logs_set_with_null_id_and_previous_goal(path):
    store = MemoryStore(path)
    store.set_wallet_goal("aposentadoria")
    store.set_wallet_goal("independência financeira")

    first, second = _log(path)
    assert (first["op"], first["collection"], first["id"]) == (
        "set",
        "wallet_goal",
        None,
    )
    assert first["before"] is None
    assert second["before"]["text"] == "aposentadoria"
    assert second["after"]["text"] == "independência financeira"


def test_each_triggered_alert_gets_its_own_trigger_line(path):
    store = MemoryStore(path)
    first = store.create_price_alert("PETR4", "below", 30.0)
    second = store.create_price_alert("VALE3", "above", 50.0)
    store.evaluate_alerts({"PETR4": 25.0, "VALE3": 60.0})

    triggers = [line for line in _log(path) if line["op"] == "trigger"]
    assert sorted(t["id"] for t in triggers) == [first["id"], second["id"]]
    assert all(t["before"]["state"] == "active" for t in triggers)
    assert all(t["after"]["state"] == "triggered" for t in triggers)


def test_deduplicated_insight_writes_no_new_line(path):
    store = MemoryStore(path)
    store.log_insight("k", "fp", "primeira")
    store.log_insight("k", "fp", "segunda")
    assert len(_log(path)) == 1


def test_line_shape_and_enums(path):
    store = MemoryStore(path)
    store.save_rule("r")
    store.set_wallet_goal("g")
    for line in _log(path):
        assert set(line) == {"ts", "pid", "op", "collection", "id", "before", "after"}
        assert line["op"] in OPS
        assert line["collection"] in COLLECTIONS
        assert line["pid"] == os.getpid()
        assert line["ts"]


def test_unwritable_log_does_not_stop_the_memory_write(path, capsys):
    os.mkdir(f"{path}.log")
    store = MemoryStore(path)

    store.save_rule("gravada mesmo assim")

    assert [r["text"] for r in MemoryStore(path).get_rules()] == ["gravada mesmo assim"]
    err = capsys.readouterr().err
    assert f"{path}.log" in err
    assert "seguiu normalmente" in err


def test_changelog_message_lives_in_bootstrap():
    message = bootstrap.CHANGELOG_FAILED_MESSAGE.format(path="p.log", cause="c")
    assert "p.log" in message and "c" in message


def test_failed_save_is_still_logged(path, monkeypatch):
    store = MemoryStore(path)
    monkeypatch.setattr(
        "investidor10_wallet.memory_store.os.replace",
        lambda *args: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(MemoryUnavailableError):
        store.save_rule("tentativa")
    monkeypatch.undo()

    lines = _log(path)
    assert [(line["op"], line["after"]["text"]) for line in lines] == [
        ("create", "tentativa")
    ]
    assert MemoryStore(path).get_rules() == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: file mode bits")
def test_log_is_created_with_private_permissions(path):
    MemoryStore(path).save_rule("r")
    assert os.stat(f"{path}.log").st_mode & 0o777 == 0o600


def test_log_sits_next_to_a_custom_memory_path(tmp_path):
    custom = tmp_path / "elsewhere"
    custom.mkdir()
    store = MemoryStore(str(custom / "mem.json"))
    store.save_rule("r")
    assert (custom / "mem.json.log").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: file mode bits")
def test_preexisting_wide_log_is_tightened_on_the_next_write(path):
    log_path = f"{path}.log"
    with open(log_path, "w", encoding="utf-8"):
        pass
    os.chmod(log_path, 0o644)

    MemoryStore(path).save_rule("r")

    assert os.stat(log_path).st_mode & 0o777 == 0o600


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX-only: symlinks and O_NOFOLLOW"
)
def test_changelog_never_follows_a_symlink(path, capsys):
    victim = os.path.join(os.path.dirname(path), "victim")
    with open(victim, "w", encoding="utf-8") as f:
        f.write("untouched")
    os.chmod(victim, 0o644)
    os.symlink(victim, f"{path}.log")

    MemoryStore(path).save_rule("r")

    with open(victim, encoding="utf-8") as f:
        assert f.read() == "untouched"
    assert os.stat(victim).st_mode & 0o777 == 0o644
    assert "não foi possível registrar" in capsys.readouterr().err
    assert [rule["text"] for rule in MemoryStore(path).get_rules()] == ["r"]


def test_failed_tighten_warns_the_operator(path, monkeypatch, capsys):
    def denied(*args, **kwargs):
        raise PermissionError("not the owner")

    monkeypatch.setattr(os, "fchmod", denied, raising=False)
    monkeypatch.setattr(os, "chmod", denied)

    MemoryStore(path).save_rule("r")

    assert "não foi possível restringir" in capsys.readouterr().err
    assert len(_log(path)) == 1
