import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-no-wallet-id"
FAKE_ID = "8765432"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX shell script and git on PATH"
)


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "notes.md").write_text("nothing secret here\n", encoding="utf-8")
    _git(tmp_path, "add", "notes.md")
    return tmp_path


def _run(cwd, wallet_id=FAKE_ID):
    env = {k: v for k, v in os.environ.items() if k != "WALLET_ID"}
    if wallet_id is not None:
        env["WALLET_ID"] = wallet_id
    return subprocess.run(
        ["sh", str(SCRIPT)],
        check=False,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def test_passes_when_no_tracked_file_has_the_id(repo):
    result = _run(repo)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""


def test_fails_and_names_the_file_without_printing_the_id(repo):
    (repo / "report.md").write_text(f"carteira {FAKE_ID}\n", encoding="utf-8")
    _git(repo, "add", "report.md")

    result = _run(repo)

    assert result.returncode == 1
    assert "report.md" in result.stderr
    assert FAKE_ID not in result.stdout + result.stderr


def test_only_tracked_files_are_checked(repo):
    (repo / "local.json").write_text(FAKE_ID, encoding="utf-8")

    assert _run(repo).returncode == 0


def test_skips_with_a_warning_when_the_id_is_not_set(repo):
    (repo / "report.md").write_text(f"carteira {FAKE_ID}\n", encoding="utf-8")
    _git(repo, "add", "report.md")

    result = _run(repo, wallet_id=None)

    assert result.returncode == 0
    assert "skipping" in result.stderr


def test_the_script_itself_does_not_contain_a_wallet_id():
    text = SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"[0-9]{6,}", text) is None
