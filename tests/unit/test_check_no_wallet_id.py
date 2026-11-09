import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-no-wallet-id"
FAKE_ID = "8765432"
FAKE_HASH = "Zq9_credential-K3"

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


def _run(cwd, wallet_id=FAKE_ID, wallet_hash=FAKE_HASH):
    env = {k: v for k, v in os.environ.items() if k not in ("WALLET_ID", "WALLET_HASH")}
    if wallet_id is not None:
        env["WALLET_ID"] = wallet_id
    if wallet_hash is not None:
        env["WALLET_HASH"] = wallet_hash
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


def _mcpb(path, name, content):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)


def test_fails_when_the_credential_is_in_a_tracked_file_without_printing_it(repo):
    (repo / "notes2.md").write_text(f"link ?h={FAKE_HASH}\n", encoding="utf-8")
    _git(repo, "add", "notes2.md")

    result = _run(repo)

    assert result.returncode == 1
    assert "notes2.md" in result.stderr
    assert FAKE_HASH not in result.stdout + result.stderr


def test_fails_when_the_credential_is_inside_a_tracked_mcpb(repo):
    package = repo / "carteira.mcpb"
    _mcpb(package, "manifest.json", f'{{"hash": "{FAKE_HASH}"}}')
    _git(repo, "add", "carteira.mcpb")

    result = _run(repo)

    assert result.returncode == 1
    assert "carteira.mcpb" in result.stderr
    assert FAKE_HASH not in result.stdout + result.stderr


def test_fails_when_the_wallet_id_is_inside_a_tracked_mcpb(repo):
    package = repo / "carteira.mcpb"
    _mcpb(package, "manifest.json", f'{{"wallet": "{FAKE_ID}"}}')
    _git(repo, "add", "carteira.mcpb")

    result = _run(repo)

    assert result.returncode == 1
    assert "carteira.mcpb" in result.stderr
    assert FAKE_ID not in result.stdout + result.stderr


def test_passes_with_a_clean_tracked_mcpb(repo):
    package = repo / "carteira.mcpb"
    _mcpb(package, "manifest.json", '{"name": "carteira"}')
    _git(repo, "add", "carteira.mcpb")

    result = _run(repo)

    assert result.returncode == 0
    assert result.stdout == result.stderr == ""


def test_an_untracked_mcpb_is_not_checked(repo):
    _mcpb(repo / "carteira.mcpb", "manifest.json", FAKE_HASH)

    assert _run(repo).returncode == 0


def test_skips_the_credential_with_a_warning_when_it_is_not_set(repo):
    (repo / "notes2.md").write_text(f"link ?h={FAKE_HASH}\n", encoding="utf-8")
    _git(repo, "add", "notes2.md")

    result = _run(repo, wallet_hash=None)

    assert result.returncode == 0
    assert "WALLET_HASH" in result.stderr
    assert "skipping" in result.stderr


def test_still_checks_the_wallet_id_when_the_credential_is_not_set(repo):
    (repo / "report.md").write_text(f"carteira {FAKE_ID}\n", encoding="utf-8")
    _git(repo, "add", "report.md")

    result = _run(repo, wallet_hash=None)

    assert result.returncode == 1


def test_still_checks_the_credential_when_the_wallet_id_is_not_set(repo):
    (repo / "notes2.md").write_text(f"link ?h={FAKE_HASH}\n", encoding="utf-8")
    _git(repo, "add", "notes2.md")

    result = _run(repo, wallet_id=None)

    assert result.returncode == 1
    assert FAKE_HASH not in result.stdout + result.stderr
