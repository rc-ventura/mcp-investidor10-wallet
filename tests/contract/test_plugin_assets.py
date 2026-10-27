import json
import re
import stat
from pathlib import Path

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
    return json.loads(path.read_text())


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
        content = path.read_text()
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content
        assert "get_session_context" in content


def test_gemini_commands_mirror_the_skills():
    command_files = sorted((PLUGIN / "commands").glob("*.toml"))
    assert len(command_files) == 3
    for path in command_files:
        content = path.read_text()
        assert "prompt =" in content
        assert "description =" in content
        assert "get_session_context" in content


def test_hooks_cover_persona_and_memory_reminder():
    hooks = _load(PLUGIN / "hooks" / "hooks.json")["hooks"]
    assert set(hooks) == {"SessionStart", "Stop"}
    persona = (PLUGIN / "hooks" / "session-start-persona.sh").read_text()
    assert "additionalContext" in persona
    assert "assistente de investimentos" in persona
    reminder = (PLUGIN / "hooks" / "stop-memory-reminder.sh").read_text()
    assert "confirmação" in reminder
    for script in ("session-start-persona.sh", "stop-memory-reminder.sh"):
        path = PLUGIN / "hooks" / script
        assert path.stat().st_mode & stat.S_IXUSR


def test_no_asset_touches_memory_file():
    for path in ASSETS:
        assert "memory.json" not in path.read_text()


def test_no_emoji_and_no_wallet_id_literals_in_assets():
    for path in ASSETS:
        content = path.read_text()
        assert not re.search(r"[\U0001F300-\U0001FAFF]", content)
        if path.suffix in (".md", ".json", ".toml"):
            assert not re.search(r"WALLET_ID\s*[:=]\s*\d+", content)
