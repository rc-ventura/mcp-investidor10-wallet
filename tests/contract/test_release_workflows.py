import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
SHA_PIN = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(workflow):
    return workflow.get("on", workflow.get(True))


def _steps(workflow):
    return [step for job in workflow["jobs"].values() for step in job["steps"]]


def test_ci_runs_on_push_and_pull_request_for_main_and_develop():
    triggers = _triggers(_load("ci.yml"))
    assert set(triggers) == {"push", "pull_request"}
    assert set(triggers["push"]["branches"]) == {"main", "develop"}
    assert set(triggers["pull_request"]["branches"]) == {"main", "develop"}


def test_main_gate_runs_only_on_pull_requests_to_main():
    triggers = _triggers(_load("main-gate.yml"))
    assert set(triggers) == {"pull_request"}
    assert triggers["pull_request"]["branches"] == ["main"]


def test_main_gate_has_read_only_permissions():
    workflow = _load("main-gate.yml")
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert "permissions" not in job or job["permissions"] == {"contents": "read"}


def test_main_gate_checks_out_full_history_with_tags():
    checkouts = [
        step
        for step in _steps(_load("main-gate.yml"))
        if str(step.get("uses", "")).startswith("actions/checkout@")
    ]
    assert checkouts
    for step in checkouts:
        options = step.get("with", {})
        assert options.get("fetch-depth") == 0
        assert options.get("fetch-tags", True) is True


def test_main_gate_calls_the_promotion_check_with_the_pull_request_head():
    runs = "\n".join(step.get("run", "") for step in _steps(_load("main-gate.yml")))
    assert "scripts/check_promotion.py" in runs
    for option in ("--head-ref", "--head-sha"):
        assert option in runs
    assert "github.head_ref" in str(_load("main-gate.yml"))
    assert "github.event.pull_request.head.sha" in str(_load("main-gate.yml"))


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_every_action_is_pinned_by_sha(path):
    for step in _steps(yaml.safe_load(path.read_text(encoding="utf-8"))):
        uses = step.get("uses")
        if uses and not uses.startswith("./"):
            assert SHA_PIN.match(uses), f"{path.name}: {uses}"


def _promote():
    return _load("promote.yml")


def test_promote_runs_after_a_successful_release_or_by_hand_with_dry_run():
    triggers = _triggers(_promote())
    assert set(triggers) == {"workflow_run", "workflow_dispatch"}
    assert triggers["workflow_run"]["workflows"] == ["Release"]
    assert triggers["workflow_run"]["types"] == ["completed"]
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"tag", "dry-run"}
    assert inputs["dry-run"]["type"] == "boolean"
    assert inputs["dry-run"]["default"] is True


def test_promote_job_requires_a_successful_release_and_a_final_tag():
    job = next(iter(_promote()["jobs"].values()))
    condition = job["if"]
    assert "github.event.workflow_run.conclusion == 'success'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "rc" in condition


def test_promote_writes_only_contents_and_pull_requests():
    workflow = _promote()
    assert workflow["permissions"] == {"contents": "read"}
    job = next(iter(workflow["jobs"].values()))
    assert job["permissions"] == {"contents": "write", "pull-requests": "write"}


def test_promote_calls_the_plan_script_with_full_history_and_no_inline_inputs():
    workflow = _promote()
    steps = _steps(workflow)
    checkout = next(
        s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout["with"]["fetch-depth"] == 0
    runs = "\n".join(step.get("run", "") for step in steps)
    assert "scripts/plan_promotion.py" in runs
    assert "--apply" in runs
    assert "${{" not in runs


def test_ci_validates_the_plugin_and_the_marketplace_with_a_pinned_cli():
    runs = "\n".join(step.get("run", "") for step in _steps(_load("ci.yml")))
    assert re.search(
        r"@anthropic-ai/claude-code@\d+\.\d+\.\d+ plugin validate \./plugin", runs
    )
    assert re.search(
        r"@anthropic-ai/claude-code@\d+\.\d+\.\d+ plugin validate \.(\s|$)", runs
    )


def test_release_verify_shares_the_uv_python_and_cache_dirs_with_the_smoke_child():
    verify = _load("release.yml")["jobs"]["verify"]
    exported = "\n".join(
        step.get("run", "")
        for step in verify["steps"]
        if "GITHUB_ENV" in step.get("run", "")
    )
    assert "UV_PYTHON_INSTALL_DIR=" in exported
    assert "UV_CACHE_DIR=" in exported
