import json
import re
from pathlib import Path

import yaml
from fastmcp import Client

from investidor10_wallet import __version__
from investidor10_wallet.server import mcp

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
MANIFESTS = [
    REPO / "plugin" / ".claude-plugin" / "plugin.json",
    REPO / "plugin" / ".codex-plugin" / "plugin.json",
    REPO / "plugin" / ".devin-plugin" / "plugin.json",
    REPO / "plugin" / "gemini-extension.json",
]
EXPECTED_TOOLS = re.compile(r"--expected-tools\s+(\d+)")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    return workflow.get("on", workflow.get(True))


def test_consistency_package_manifests_and_plugin_server_share_one_version():
    assert {_json(path)["version"] for path in MANIFESTS} == {__version__}
    server_args = _json(MANIFESTS[0])["mcpServers"]["carteira"]["args"]
    assert f"mcp-investidor10-wallet=={__version__}" in server_args


async def test_consistency_release_smoke_expects_the_tools_the_server_serves():
    async with Client(mcp) as client:
        served = len(await client.list_tools())
    release = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    expected = {int(n) for n in EXPECTED_TOOLS.findall(release)}
    assert expected == {served}


def test_consistency_live_workflow_only_runs_on_schedule_and_by_hand():
    workflow = _yaml(WORKFLOWS / "live.yml")
    assert set(_triggers(workflow)) == {"schedule", "workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    runs = "\n".join(
        step.get("run", "")
        for job in workflow["jobs"].values()
        for step in job["steps"]
    )
    assert "pytest -m live" in runs


def test_consistency_live_workflow_reads_the_wallet_only_from_secrets():
    text = (WORKFLOWS / "live.yml").read_text(encoding="utf-8")
    env = {}
    for job in _yaml(WORKFLOWS / "live.yml")["jobs"].values():
        env.update(job.get("env", {}))
        for step in job["steps"]:
            env.update(step.get("env", {}))
    assert env["WALLET_ID"] == "${{ secrets.LIVE_WALLET_ID }}"
    assert not re.search(r"\b\d{6,}\b", text)


def test_consistency_dependabot_covers_uv_and_github_actions_weekly():
    config = _yaml(REPO / ".github" / "dependabot.yml")
    assert config["version"] == 2
    updates = {item["package-ecosystem"]: item for item in config["updates"]}
    assert set(updates) == {"uv", "github-actions"}
    for item in updates.values():
        assert item["directory"] == "/"
        assert item["schedule"]["interval"] == "weekly"
        assert item["target-branch"] == "develop"
        assert item["cooldown"]["default-days"] >= 7
