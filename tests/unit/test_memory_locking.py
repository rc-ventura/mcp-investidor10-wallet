import errno
import glob
import json
import os
import sys
import threading

import filelock
import pytest

from investidor10_wallet import bootstrap, memory_store
from investidor10_wallet.memory_store import (
    MemoryBusyError,
    MemoryReadOnlyError,
    MemoryStore,
    MemoryUnavailableError,
)


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "memory.json")


def _rewrite(path, mutate):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    mutate(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_read_reflects_edit_made_by_another_writer(path):
    store = MemoryStore(path)
    store.save_rule("first")

    def add_rule(data):
        data["rules"].append({"id": 2, "text": "second", "created_at": "x"})

    _rewrite(path, add_rule)

    assert [r["text"] for r in store.get_rules()] == ["first", "second"]


def test_corrupted_store_recovers_after_manual_repair(path):
    store = MemoryStore(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{broken")
    with pytest.raises(MemoryUnavailableError):
        store.get_rules()
    assert not store.available

    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory_store._empty_store(), f)

    assert store.get_rules() == []
    assert store.available


def test_write_fails_with_busy_error_when_lock_is_held_elsewhere(path):
    store = MemoryStore(path, lock_timeout=0.2)
    store.save_rule("kept")
    other = filelock.FileLock(f"{path}.lock")
    with other:
        with pytest.raises(MemoryBusyError) as exc:
            store.save_rule("blocked")
        assert exc.value.code == "memory_busy"
    assert [r["text"] for r in MemoryStore(path).get_rules()] == ["kept"]


def test_read_also_fails_with_busy_error_when_lock_is_held_elsewhere(path):
    store = MemoryStore(path, lock_timeout=0.2)
    with filelock.FileLock(f"{path}.lock"), pytest.raises(MemoryBusyError):
        store.get_rules()


def _no_flock(monkeypatch):
    def refuse(self, *args, **kwargs):
        raise OSError(errno.ENOSYS, "Function not implemented")

    monkeypatch.setattr(filelock.FileLock, "acquire", refuse)


def test_filesystem_without_lock_support_makes_store_read_only(
    path, monkeypatch, capsys
):
    MemoryStore(path).save_rule("kept")
    _no_flock(monkeypatch)

    store = MemoryStore(path)

    assert store.read_only is True
    assert store.available is True
    assert [r["text"] for r in store.get_rules()] == ["kept"]
    with pytest.raises(MemoryReadOnlyError) as exc:
        store.save_rule("refused")
    assert exc.value.code == "memory_read_only"
    assert path in str(exc.value)
    assert bootstrap.LOCK_UNSUPPORTED_MESSAGE.format(path=path) in (
        capsys.readouterr().err
    )
    monkeypatch.undo()
    assert [r["text"] for r in MemoryStore(path).get_rules()] == ["kept"]


def test_read_only_store_never_creates_the_memory_file(path, monkeypatch):
    _no_flock(monkeypatch)
    store = MemoryStore(path)
    assert store.get_rules() == []
    monkeypatch.undo()
    assert not glob.glob(path)


def test_two_stores_over_the_same_corrupted_file_make_one_backup(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("{broken")
    first = MemoryStore(path)
    second = MemoryStore(path)
    for store in (first, second):
        with pytest.raises(MemoryUnavailableError):
            store.get_rules()
    assert len(glob.glob(path + ".broken-*")) == 1


def test_different_corrupted_content_makes_a_second_backup(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("{broken")
    MemoryStore(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{also broken")
    MemoryStore(path)
    assert len(glob.glob(path + ".broken-*")) == 2


def _flaky_replace(monkeypatch, failures):
    real = memory_store.os.replace
    calls = {"count": 0}

    def replace(src, dst):
        calls["count"] += 1
        if failures is None or calls["count"] <= failures:
            raise PermissionError("file is in use")
        return real(src, dst)

    sleeps = []
    monkeypatch.setattr(memory_store.os, "replace", replace)
    monkeypatch.setattr(memory_store.time, "sleep", sleeps.append)
    return sleeps


def test_replace_is_retried_with_backoff_while_file_is_in_use(path, monkeypatch):
    store = MemoryStore(path)
    sleeps = _flaky_replace(monkeypatch, failures=3)

    store.save_rule("eventually written")

    assert sleeps == [0.05, 0.1, 0.2]
    monkeypatch.undo()
    assert [r["text"] for r in MemoryStore(path).get_rules()] == ["eventually written"]


def test_replace_that_never_succeeds_degrades_without_touching_the_file(
    path, tmp_path, monkeypatch
):
    store = MemoryStore(path)
    store.save_rule("kept")
    sleeps = _flaky_replace(monkeypatch, failures=None)

    with pytest.raises(MemoryUnavailableError):
        store.save_rule("lost")

    assert sleeps == [0.05, 0.1, 0.2, 0.4, 0.8]
    assert list(tmp_path.glob(".memory-*")) == []
    monkeypatch.undo()
    assert [r["text"] for r in MemoryStore(path).get_rules()] == ["kept"]


def test_two_stores_never_hand_out_the_same_id(path):
    first = MemoryStore(path)
    second = MemoryStore(path)
    ids = []
    for store in (first, second, first, second):
        ids.append(store.save_rule("r")["id"])
    assert ids == [1, 2, 3, 4]


def test_log_insight_dedupe_and_add_share_one_critical_section(path):
    first = MemoryStore(path)
    second = MemoryStore(path)
    first.log_insight("concentration", "PETR4:15>8", "first")
    result = second.log_insight("concentration", "PETR4:15>8", "second")
    assert result["already_logged"] is True
    assert len(first.get_all("insights_log")) == 1


def test_memory_in_a_missing_directory_degrades_instead_of_creating_it(tmp_path):
    missing = tmp_path / "missing"
    store = MemoryStore(str(missing / "memory.json"))
    assert not store.available
    assert not missing.exists()
    with pytest.raises(MemoryUnavailableError):
        store.get_wallet_goal()


@pytest.fixture
def umask_022():
    previous = os.umask(0o022)
    yield
    os.umask(previous)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: file mode bits")
def test_lock_file_is_created_private_even_under_a_permissive_umask(path, umask_022):
    MemoryStore(path)
    assert os.stat(f"{path}.lock").st_mode & 0o777 == 0o600


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: file mode bits")
def test_preexisting_wide_lock_file_is_tightened(path, umask_022):
    lock_path = f"{path}.lock"
    with open(lock_path, "w", encoding="utf-8"):
        pass
    os.chmod(lock_path, 0o644)

    MemoryStore(path)

    assert os.stat(lock_path).st_mode & 0o777 == 0o600


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlink creation")
def test_lock_path_that_is_a_symlink_is_refused_and_the_target_is_untouched(
    tmp_path, path
):
    victim = tmp_path / "victim"
    victim.write_text("VICTIM-DATA", encoding="utf-8")
    victim.chmod(0o644)
    os.symlink(victim, f"{path}.lock")

    store = MemoryStore(path)

    assert store.available is False
    with pytest.raises(MemoryUnavailableError):
        store.get_rules()
    assert victim.read_text(encoding="utf-8") == "VICTIM-DATA"
    assert victim.stat().st_mode & 0o777 == 0o644


def test_full_kernel_lock_table_fails_one_operation_and_then_recovers(
    path, monkeypatch
):
    store = MemoryStore(path)
    real_acquire = filelock.FileLock.acquire
    failures = iter([True])

    def flaky(self, *args, **kwargs):
        if next(failures, False):
            raise OSError(errno.ENOLCK, "No locks available")
        return real_acquire(self, *args, **kwargs)

    monkeypatch.setattr(filelock.FileLock, "acquire", flaky)

    with pytest.raises(MemoryUnavailableError) as exc:
        store.save_rule("first try")
    assert exc.value.code == "memory_unavailable"
    assert store.read_only is False  # transient: never latched
    store.save_rule("second try")
    assert [r["text"] for r in store.get_rules()] == ["second try"]


def test_a_second_thread_never_slips_past_the_lock(path):
    store = MemoryStore(path, lock_timeout=0.2)
    entered = threading.Event()
    release = threading.Event()

    def holder():
        with store._locked():
            entered.set()
            release.wait(5)

    thread = threading.Thread(target=holder)
    thread.start()
    assert entered.wait(5)
    try:
        with pytest.raises(MemoryBusyError):
            store.save_rule("from another thread")
    finally:
        release.set()
        thread.join(5)

    store.save_rule("after release")
    assert [r["text"] for r in store.get_rules()] == ["after release"]


def test_nested_calls_in_one_thread_stay_reentrant(path):
    store = MemoryStore(path, lock_timeout=0.2)
    with store._locked():
        store.save_rule("nested")
    assert [r["text"] for r in store.get_rules()] == ["nested"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlinks")
def test_lock_tighten_never_follows_a_symlink(path, capsys):
    victim = os.path.join(os.path.dirname(path), "victim")
    with open(victim, "w", encoding="utf-8") as f:
        f.write("x")
    os.chmod(victim, 0o644)
    link = f"{path}.lock-link"
    os.symlink(victim, link)

    MemoryStore(path)._tighten_by_path(link)

    assert os.stat(victim).st_mode & 0o777 == 0o644
    assert "não foi possível restringir" in capsys.readouterr().err
