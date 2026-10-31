import json
import re
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugin"
CLAUDE_MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"
DEVIN_MANIFEST = PLUGIN / ".devin-plugin" / "plugin.json"
CODEX_MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
GEMINI_MANIFEST = PLUGIN / "gemini-extension.json"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
ASSETS = sorted(p for p in PLUGIN.rglob("*") if p.is_file())

MANIFESTS = [CLAUDE_MANIFEST, DEVIN_MANIFEST, CODEX_MANIFEST, GEMINI_MANIFEST]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifests_are_valid_json_with_matching_names():
    data = [_load(path) for path in MANIFESTS]
    names = {m["name"] for m in data}
    versions = {m["version"] for m in data}
    assert names == {"investidor10-carteira"}
    assert len(versions) == 1
    assert all(m["description"] for m in data)
    market = _load(MARKETPLACE)
    assert market["plugins"][0]["name"] == data[0]["name"]
    assert "owner" in market


def test_plugin_carries_no_mcp_server():
    assert not (PLUGIN / ".mcp.json").exists()
    for path in MANIFESTS:
        assert "mcpServers" not in _load(path)


def test_all_declared_paths_exist():
    for plugin in _load(MARKETPLACE)["plugins"]:
        assert (REPO / plugin["source"].removeprefix("./")).exists()
    codex = _load(CODEX_MANIFEST)
    for key in ("skills", "apps"):
        if key in codex:
            assert (PLUGIN / codex[key].removeprefix("./")).exists()


def test_skills_present_with_required_frontmatter():
    skill_files = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert len(skill_files) == 3
    for path in skill_files:
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content
        assert "get_session_context" in content


def test_gemini_commands_mirror_the_skills():
    command_files = sorted((PLUGIN / "commands").glob("*.toml"))
    assert len(command_files) == 3
    for path in command_files:
        content = path.read_text(encoding="utf-8")
        assert "prompt =" in content
        assert "description =" in content
        assert "get_session_context" in content


def test_hooks_cover_persona_and_memory_reminder():
    hooks = _load(PLUGIN / "hooks" / "hooks.json")["hooks"]
    assert set(hooks) == {"SessionStart", "Stop"}
    persona = (PLUGIN / "hooks" / "session-start-persona.sh").read_text(
        encoding="utf-8"
    )
    assert "additionalContext" in persona
    assert "assistente de investimentos" in persona
    reminder = (PLUGIN / "hooks" / "stop-memory-reminder.sh").read_text(
        encoding="utf-8"
    )
    assert "confirmação" in reminder


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: executable bit")
def test_hook_scripts_are_executable():
    for script in ("session-start-persona.sh", "stop-memory-reminder.sh"):
        path = PLUGIN / "hooks" / script
        assert path.stat().st_mode & stat.S_IXUSR


def test_no_asset_touches_memory_file():
    for path in ASSETS:
        assert "memory.json" not in path.read_text(encoding="utf-8")


def test_no_emoji_and_no_wallet_id_literals_in_assets():
    for path in ASSETS:
        content = path.read_text(encoding="utf-8")
        assert not re.search(r"[\U0001F300-\U0001FAFF]", content)
        if path.suffix in (".md", ".json", ".toml"):
            assert not re.search(r"WALLET_ID\s*[:=]\s*\d+", content)


def _bash():
    if sys.platform != "win32":
        return "bash"
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    pytest.skip("Git Bash not found; the bash on PATH is the WSL launcher")


def test_hooks_scripts_fail_open_on_empty_input():
    import subprocess

    bash = _bash()
    for script in ("session-start-persona.sh", "stop-memory-reminder.sh"):
        path = PLUGIN / "hooks" / script
        proc = subprocess.run(
            [bash, path.as_posix()],
            check=False,
            input="{}",
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert proc.returncode == 0, (
            f"{script} saiu com {proc.returncode}: {proc.stderr}"
        )
        if script == "session-start-persona.sh":
            assert "additionalContext" in proc.stdout
        else:
            assert proc.stdout == ""


def test_dividends_skill_and_its_mirror_handle_privacy_mode():
    skill = (PLUGIN / "skills" / "resumo-de-dividendos" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    command = (PLUGIN / "commands" / "resumo-de-dividendos.toml").read_text(
        encoding="utf-8"
    )
    for content in (skill, command):
        assert "privacy_mode_unavailable" in content
        assert "get_wallet_positions" in content
        assert "não estime" in content
