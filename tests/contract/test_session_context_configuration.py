import json

import pytest
from fastmcp import Client

from investidor10_wallet import server, wallet_config
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

WALLET = "9876542"
CREDENTIAL = "Kp3_credential-W8"


@pytest.fixture(autouse=True)
def memory(tmp_path, monkeypatch):
    store = MemoryStore(str(tmp_path / "memory.json"))
    monkeypatch.setattr(server, "memory", store)
    return store


@pytest.fixture
def no_environment(monkeypatch):
    monkeypatch.delenv("WALLET_ID", raising=False)
    monkeypatch.delenv("WALLET_MASK_VALUES", raising=False)


def _write(home, share_hash=CREDENTIAL, mask_values=False):
    wallet_config.write_config(
        home,
        wallet_config.LocalConfig(
            wallet_id=WALLET,
            share_hash=share_hash,
            mode="restricted" if share_hash else "public",
            mask_values=mask_values,
            validated_at="2026-11-06T10:00:00-03:00",
            source="setup_page",
        ),
    )


def _config_file(home):
    path = wallet_config.config_path(home)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    return path


async def _context():
    async with Client(mcp) as client:
        result = await client.call_tool("get_session_context", {}, raise_on_error=False)
    assert result.is_error is False
    return result.structured_content, result.content[0].text


async def test_pending_without_file_or_environment_points_to_the_setup_tool(
    no_environment, memory
):
    memory.save_rule("kept while pending")

    context, _ = await _context()

    assert context["configuration"]["status"] == "pending"
    assert context["configuration"]["reason"] == "missing"
    assert "open_wallet_setup" in context["configuration"]["next_action"]
    assert context["memory_status"] == "ok"
    assert context["memory"]["rules"][0]["text"] == "kept while pending"


async def test_pending_for_a_corrupted_file(no_environment, isolated_home):
    _config_file(isolated_home).write_text("{broken", encoding="utf-8")

    context, _ = await _context()

    assert context["configuration"]["status"] == "pending"
    assert context["configuration"]["reason"] == "unreadable"


async def test_pending_for_a_file_from_a_future_version(no_environment, isolated_home):
    _config_file(isolated_home).write_text(json.dumps({"version": 2}), encoding="utf-8")

    context, _ = await _context()

    assert context["configuration"]["reason"] == "future_version"


async def test_configured_from_the_file_shows_only_the_masked_wallet(
    no_environment, isolated_home
):
    _write(isolated_home)

    context, text = await _context()

    assert context["configuration"] == {
        "status": "configured",
        "mode": "restricted",
        "mask_values": False,
        "wallet": "…42",
        "origin": "file",
    }
    assert WALLET not in text
    assert CREDENTIAL not in text


async def test_configured_from_the_environment_is_public(monkeypatch):
    monkeypatch.setenv("WALLET_ID", "1234567")

    context, text = await _context()

    assert context["configuration"]["status"] == "configured"
    assert context["configuration"]["origin"] == "environment"
    assert context["configuration"]["mode"] == "public"
    assert "1234567" not in text


async def test_the_file_wins_over_the_environment(monkeypatch, isolated_home):
    monkeypatch.setenv("WALLET_ID", "1234567")
    _write(isolated_home)

    context, _ = await _context()

    assert context["configuration"]["origin"] == "file"
    assert context["configuration"]["wallet"] == "…42"


async def test_effective_mask_is_file_or_environment(monkeypatch, isolated_home):
    _write(isolated_home, mask_values=False)
    monkeypatch.setenv("WALLET_MASK_VALUES", "1")

    context, _ = await _context()

    assert context["configuration"]["mask_values"] is True


async def test_mask_from_the_file_is_reported(no_environment, isolated_home):
    _write(isolated_home, mask_values=True)

    context, _ = await _context()

    assert context["configuration"]["mask_values"] is True


async def test_configuration_block_is_present_when_memory_is_unavailable(
    no_environment, tmp_path, monkeypatch
):
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(server, "memory", MemoryStore(str(path)))

    context, _ = await _context()

    assert context["memory_status"] == "unavailable"
    assert context["configuration"]["status"] == "pending"


async def test_the_server_exposes_twenty_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
    assert len(tools) == 20
    assert "open_wallet_setup" in {tool.name for tool in tools}
