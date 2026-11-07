import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


def _workflow():
    return yaml.safe_load(RELEASE.read_text(encoding="utf-8"))


def _text():
    return RELEASE.read_text(encoding="utf-8")


def _job(name):
    return _workflow()["jobs"][name]


def _runs(job):
    return "\n".join(step.get("run", "") for step in job["steps"])


def _uses(job):
    return [step.get("uses", "") for step in job["steps"]]


def test_release_runs_on_version_tags_including_release_candidates():
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"push"}
    patterns = triggers["push"]["tags"]
    assert patterns == ["v*"]
    assert re.fullmatch(patterns[0].replace("*", ".*"), "v0.4.0rc1")


def test_the_top_level_permissions_are_read_only():
    assert _workflow()["permissions"] == {"contents": "read"}


def test_jobs_are_build_publish_and_verify():
    assert set(_workflow()["jobs"]) == {"build", "publish", "verify"}


def test_build_has_no_publishing_permission():
    build = _job("build")
    assert "id-token" not in str(build.get("permissions", {}))
    assert "environment" not in build


def test_build_checks_the_tag_the_changelog_and_smokes_the_wheel():
    runs = _runs(_job("build"))
    assert "uv build" in runs
    assert "scripts/check_release_tag.py" in runs
    assert "github.ref_name" in str(_job("build"))
    assert "scripts/smoke_mcp.py" in runs
    assert "--expected-tools 20" in runs
    assert "WALLET_ID não configurado" not in _text()
    assert "expected exit 1" not in _text()
    assert any(
        uses.startswith("actions/upload-artifact@") for uses in _uses(_job("build"))
    )


def test_publish_only_publishes_with_the_only_id_token():
    publish = _job("publish")
    assert publish["needs"] == "build"
    assert publish["environment"] == "pypi"
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    uses = _uses(publish)
    assert not any(u.startswith("actions/checkout@") for u in uses)
    assert any(u.startswith("actions/download-artifact@") for u in uses)
    assert any(u.startswith("pypa/gh-action-pypi-publish@") for u in uses)
    assert "pytest" not in _runs(publish)
    assert "smoke" not in _runs(publish)
    for name in ("build", "verify"):
        assert "id-token" not in str(_job(name).get("permissions", {}))


def test_verify_installs_the_exact_version_from_the_index_on_three_systems():
    verify = _job("verify")
    assert verify["needs"] == "publish"
    assert set(verify["strategy"]["matrix"]["os"]) == {
        "ubuntu-latest",
        "macos-latest",
        "windows-latest",
    }
    runs = _runs(verify)
    assert "mcp-investidor10-wallet==" in runs
    assert "pip install" in runs
    assert "uvx" in runs
    assert runs.count("scripts/smoke_mcp.py") >= 2
    assert "--expected-tools 20" in runs
    assert "dist/" not in runs


def test_job_level_env_does_not_use_the_runner_context():
    # the runner context only exists inside steps; GitHub rejects the whole file otherwise
    for name, job in _workflow()["jobs"].items():
        for key, value in (job.get("env") or {}).items():
            assert "runner." not in str(value), (name, key)
