import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "plan_promotion.py"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="git on PATH and POSIX paths"
)


def _load():
    spec = importlib.util.spec_from_file_location("plan_promotion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


promotion = _load()


def _git(cwd, *args):
    result = subprocess.run(
        [
            "git",
            "-c", "user.email=t@t",
            "-c", "user.name=t",
            "-c", "commit.gpgsign=false",
            "-c", "tag.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )  # fmt: skip
    return result.stdout.strip()


def _commit(repo, name):
    (repo / name).write_text(name, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "develop")
    _commit(root, "base")
    return root


def _plan(repo, **kwargs):
    kwargs.setdefault("develop_ref", "develop")
    return promotion.plan(root=repo, **kwargs)


def test_final_tag_on_develop_creates_the_promote_branch_and_a_request_to_main(repo):
    sha = _commit(repo, "feature")
    _git(repo, "tag", "v0.4.0")
    actions = _plan(repo, tag="v0.4.0")
    assert [a.kind for a in actions] == ["create_branch", "open_pull_request"]
    assert actions[0].branch == "promote/v0.4.0"
    assert actions[0].sha == sha
    assert (actions[1].head, actions[1].base) == ("promote/v0.4.0", "main")


def test_hotfix_tag_outside_develop_also_returns_to_develop(repo):
    _git(repo, "checkout", "-q", "-b", "hotfix/x")
    sha = _commit(repo, "fix")
    _git(repo, "tag", "v0.4.1")
    _git(repo, "checkout", "-q", "develop")
    actions = _plan(repo, tag="v0.4.1")
    assert [a.kind for a in actions] == [
        "create_branch",
        "open_pull_request",
        "open_pull_request",
    ]
    assert actions[0].sha == sha
    assert {(a.head, a.base) for a in actions[1:]} == {
        ("promote/v0.4.1", "main"),
        ("promote/v0.4.1", "develop"),
    }


def test_release_candidate_tag_is_refused(repo):
    _git(repo, "tag", "v0.4.0rc4")
    with pytest.raises(promotion.PromotionRefused, match="pré-lançamento"):
        _plan(repo, tag="v0.4.0rc4")


@pytest.mark.parametrize("tag", ["0.4.0", "v0.4", "v0.4.0-beta", "promote/v0.4.0"])
def test_malformed_tag_is_refused(repo, tag):
    with pytest.raises(promotion.PromotionRefused):
        _plan(repo, tag=tag)


def test_missing_tag_is_refused(repo):
    with pytest.raises(promotion.PromotionRefused, match="não existe"):
        _plan(repo, tag="v9.9.9")


def test_missing_develop_ref_is_refused(repo):
    _git(repo, "tag", "v0.4.0")
    with pytest.raises(promotion.PromotionRefused, match="develop"):
        _plan(repo, tag="v0.4.0", develop_ref="origin/develop")


def test_final_tag_is_found_from_the_commit(repo):
    sha = _commit(repo, "feature")
    _git(repo, "tag", "v0.4.0rc5")
    _git(repo, "tag", "v0.4.0")
    assert promotion.final_tag_at(repo, sha) == "v0.4.0"


def test_commit_with_only_a_release_candidate_tag_has_no_final_tag(repo):
    sha = _commit(repo, "feature")
    _git(repo, "tag", "v0.4.0rc5")
    assert promotion.final_tag_at(repo, sha) is None


def _run(repo, *args):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--develop-ref",
            "develop",
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_dry_run_prints_the_actions_in_pt_br_and_changes_nothing(repo):
    _git(repo, "tag", "v0.4.0")
    result = _run(repo, "--tag", "v0.4.0")
    assert result.returncode == 0
    assert "promote/v0.4.0" in result.stdout
    assert "main" in result.stdout
    assert "simulação" in result.stdout.lower()
    assert "promote/v0.4.0" not in _git(repo, "branch", "--list")


def test_sha_without_a_final_tag_exits_cleanly_with_nothing_to_promote(repo):
    sha = _commit(repo, "feature")
    _git(repo, "tag", "v0.4.0rc5")
    result = _run(repo, "--sha", sha)
    assert result.returncode == 0
    assert "nada a promover" in result.stdout.lower()


def test_refused_tag_exits_1_with_the_cause_in_pt_br(repo):
    _git(repo, "tag", "v0.4.0rc4")
    result = _run(repo, "--tag", "v0.4.0rc4")
    assert result.returncode == 1
    assert "pré-lançamento" in result.stderr


def test_unknown_sha_exits_1_instead_of_saying_nothing_to_promote(repo):
    result = _run(repo, "--sha", "0" * 40)
    assert result.returncode == 1
    assert "não existe" in result.stderr
