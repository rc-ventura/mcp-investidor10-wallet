import json
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from investidor10_wallet import __version__

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
    assert versions == {__version__}
    assert all(m["description"] for m in data)
    market = _load(MARKETPLACE)
    assert market["plugins"][0]["name"] == data[0]["name"]
    assert "owner" in market


def test_only_the_claude_manifest_declares_the_server():
    assert not (PLUGIN / ".mcp.json").exists()
    for path in (DEVIN_MANIFEST, CODEX_MANIFEST, GEMINI_MANIFEST):
        assert "mcpServers" not in _load(path)
    servers = _load(CLAUDE_MANIFEST)["mcpServers"]
    assert set(servers) == {"carteira"}
    carteira = servers["carteira"]
    assert carteira["command"] == "uvx"
    assert carteira["args"] == [
        "--from",
        f"mcp-investidor10-wallet=={__version__}",
        "mcp-investidor10-wallet",
    ]
    assert "env" not in carteira


def test_claude_manifest_has_display_name_and_license():
    manifest = _load(CLAUDE_MANIFEST)
    assert manifest["displayName"]
    assert manifest["license"] == "MIT"


def test_plugin_has_no_bundled_server_or_bin_directory():
    assert not (PLUGIN / "servers").exists()
    assert not (PLUGIN / "bin").exists()


def test_all_declared_paths_exist():
    for plugin in _load(MARKETPLACE)["plugins"]:
        assert (REPO / plugin["source"].removeprefix("./")).exists()
    codex = _load(CODEX_MANIFEST)
    for key in ("skills", "apps"):
        if key in codex:
            assert (PLUGIN / codex[key].removeprefix("./")).exists()


def test_skills_present_with_required_frontmatter():
    skill_files = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert len(skill_files) == 4
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
    start = hooks["SessionStart"][0]["hooks"][0]["command"]
    assert start == 'cat "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.json"'
    stop = hooks["Stop"][0]["hooks"][0]["command"]
    assert stop == 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/stop-memory-reminder.sh"'
    reminder = (PLUGIN / "hooks" / "stop-memory-reminder.sh").read_text(
        encoding="utf-8"
    )
    assert "confirmação" in reminder


def test_session_start_is_static_ascii_json_with_persona_and_pending_rule():
    path = PLUGIN / "hooks" / "session-start.json"
    raw = path.read_bytes()
    raw.decode("ascii")
    data = json.loads(raw)
    output = data["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    context = output["additionalContext"]
    assert "assistente de investimentos" in context
    assert "get_session_context" in context
    assert "configurar-carteira" in context
    assert not (PLUGIN / "hooks" / "session-start-persona.sh").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: executable bit")
def test_hook_scripts_are_executable():
    path = PLUGIN / "hooks" / "stop-memory-reminder.sh"
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


def test_stop_hook_fails_open_on_empty_input():
    path = PLUGIN / "hooks" / "stop-memory-reminder.sh"
    proc = subprocess.run(
        [_bash(), path.as_posix()],
        check=False,
        input="{}",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, f"saiu com {proc.returncode}: {proc.stderr}"
    assert proc.stdout == ""


def test_configure_skill_follows_the_contract_steps():
    skill = (PLUGIN / "skills" / "configurar-carteira" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert skill.startswith("---")
    assert "name: configurar-carteira" in skill
    assert "description:" in skill
    for needle in (
        "open_wallet_setup",
        "get_session_context",
        "configuration",
        "mcp-investidor10-wallet configure",
        "nunca na conversa",
        "docs/INSTALACAO-DESKTOP.md",
    ):
        assert needle in skill, needle


def test_guardian_inherits_the_session_tools():
    agent = (PLUGIN / "agents" / "guardiao-de-disciplina.md").read_text(
        encoding="utf-8"
    )
    frontmatter = agent.split("---")[1]
    assert "tools:" not in frontmatter
    assert "model: inherit" in frontmatter


def test_marketplace_description_names_the_whole_product():
    plugin = _load(MARKETPLACE)["plugins"][0]
    assert plugin["source"] == "./plugin"
    assert "servidor" in plugin["description"]


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
