import os
import stat
import sys

import pytest

from investidor10_wallet import local_files

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")


@POSIX_ONLY
def test_ensure_private_dir_creates_with_0700(tmp_path):
    target = tmp_path / "a" / "b"
    local_files.ensure_private_dir(target)
    assert stat.S_IMODE(target.stat().st_mode) == 0o700


@POSIX_ONLY
def test_ensure_private_dir_refuses_symlink(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    with pytest.raises(OSError):
        local_files.ensure_private_dir(tmp_path / "link")


def test_ensure_private_dir_refuses_regular_file(tmp_path):
    (tmp_path / "file").write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        local_files.ensure_private_dir(tmp_path / "file")


@POSIX_ONLY
def test_read_bytes_refuses_symlink(tmp_path):
    target = tmp_path / "t"
    target.write_bytes(b"x")
    (tmp_path / "l").symlink_to(target)
    with pytest.raises(OSError):
        local_files.read_bytes_no_follow(tmp_path / "l")


def test_read_bytes_respects_the_limit(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"a" * 11)
    assert local_files.read_bytes_no_follow(path, limit=11) == b"a" * 11
    with pytest.raises(OSError):
        local_files.read_bytes_no_follow(path, limit=10)


@POSIX_ONLY
def test_write_private_atomic_creates_0600_and_replaces(tmp_path):
    path = tmp_path / "f.json"
    local_files.write_private_atomic(path, b"one", prefix=".f-")
    local_files.write_private_atomic(path, b"two", prefix=".f-")
    assert path.read_bytes() == b"two"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == ["f.json"]


def test_replace_with_retry_retries_permission_errors(monkeypatch):
    calls = []

    def flaky(source, destination):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("em uso")

    monkeypatch.setattr(local_files.os, "replace", flaky)
    monkeypatch.setattr(local_files, "REPLACE_RETRY_DELAYS", (0, 0, 0))
    local_files.replace_with_retry("a", "b")
    assert len(calls) == 3


def test_replace_with_retry_raises_after_last_attempt(monkeypatch):
    def always(source, destination):
        raise PermissionError("em uso")

    monkeypatch.setattr(local_files.os, "replace", always)
    monkeypatch.setattr(local_files, "REPLACE_RETRY_DELAYS", (0, 0))
    with pytest.raises(PermissionError):
        local_files.replace_with_retry("a", "b")


def test_constants_are_ints():
    assert isinstance(local_files.NO_FOLLOW, int)
    assert isinstance(local_files.BINARY, int)
    assert os.O_RDONLY == 0
