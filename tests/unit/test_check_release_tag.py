import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_release_tag.py"


def _repo(tmp_path, version, changelog):
    package = tmp_path / "src" / "investidor10_wallet"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        f'__version__ = "{version}"\n', encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return tmp_path


def _run(root, tag):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--tag", tag, "--repo-root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("version", "tag", "changelog"),
    [
        ("0.4.0", "v0.4.0", "## [0.4.0] - 2026-11-20\n"),
        ("0.4.0rc1", "v0.4.0rc1", "## [0.4.0] - não lançado\n"),
        ("0.4.0rc12", "v0.4.0rc12", "# Changelog\n\n## [0.4.0] - não lançado\n"),
        ("1.10.3", "v1.10.3", "## [1.10.3] - 2027-01-01\n"),
    ],
)
def test_accepts_a_tag_that_matches_the_version_and_the_changelog(
    tmp_path, version, tag, changelog
):
    result = _run(_repo(tmp_path, version, changelog), tag)
    assert result.returncode == 0, result.stderr


def test_a_release_candidate_looks_for_the_base_version_section(tmp_path):
    root = _repo(tmp_path, "0.4.0rc1", "## [0.4.0rc1] - 2026-11-10\n")
    result = _run(root, "v0.4.0rc1")
    assert result.returncode == 1
    assert "[0.4.0]" in result.stderr


def test_refuses_a_tag_different_from_the_package_version(tmp_path):
    root = _repo(tmp_path, "0.4.0rc1", "## [0.4.0] - não lançado\n")
    result = _run(root, "v0.4.0rc2")
    assert result.returncode == 1
    assert "__version__" in result.stderr


def test_refuses_a_missing_changelog_section(tmp_path):
    root = _repo(tmp_path, "0.4.0", "## [0.3.0] - 2026-10-28\n")
    result = _run(root, "v0.4.0")
    assert result.returncode == 1
    assert "CHANGELOG.md" in result.stderr


def test_a_section_for_a_longer_version_does_not_count(tmp_path):
    root = _repo(tmp_path, "0.4.0", "## [0.4.01] - 2026-10-28\n")
    assert _run(root, "v0.4.0").returncode == 1


@pytest.mark.parametrize(
    "tag", ["0.4.0", "v0.4", "v0.4.0-rc1", "v0.4.0.post1", "va.b.c"]
)
def test_refuses_a_malformed_tag(tmp_path, tag):
    root = _repo(tmp_path, "0.4.0", "## [0.4.0] - 2026-11-20\n")
    result = _run(root, tag)
    assert result.returncode == 1
    assert "tag" in result.stderr.lower()


def test_the_repository_itself_is_consistent_with_its_own_version():
    from investidor10_wallet import __version__

    root = SCRIPT.parents[1]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    base = __version__.split("rc")[0]
    if f"## [{base}]" not in changelog:
        pytest.skip("no changelog section yet for this version")
    assert _run(root, f"v{__version__}").returncode == 0
