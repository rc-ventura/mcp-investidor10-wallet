import json
import webbrowser

import httpx
import pytest
import respx
from fastmcp import Client

from investidor10_wallet import server, setup_page, wallet_client, wallet_config
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

PROXY = wallet_client.WALLET_PROXY_BASE_URL
WALLET = "4242420"
CREDENTIAL = "Hs7_credential-M2"
FORBIDDEN_ARGUMENTS = ("link", "hash", "credential", "wallet", "mask", "share", "url")


@pytest.fixture
def browser(monkeypatch):
    opened = []

    def fake_open(url, *args, **kwargs):
        opened.append(url)
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    return opened


@pytest.fixture(autouse=True)
def memory(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))


async def _call(tool, arguments=None):
    async with Client(mcp) as client:
        return await client.call_tool(tool, arguments or {}, raise_on_error=False)


async def _tools():
    async with Client(mcp) as client:
        return {tool.name: tool for tool in await client.list_tools()}


async def test_open_wallet_setup_takes_no_parameters():
    tool = (await _tools())["open_wallet_setup"]
    assert tool.input_schema.get("properties", {}) == {}


async def test_no_tool_receives_a_link_credential_wallet_or_mask():
    for name, tool in (await _tools()).items():
        for argument in tool.input_schema.get("properties", {}):
            lowered = argument.lower()
            assert not any(word in lowered for word in FORBIDDEN_ARGUMENTS), (
                name,
                argument,
            )


async def test_open_wallet_setup_annotations():
    annotations = (await _tools())["open_wallet_setup"].annotations
    assert annotations.read_only_hint is False
    assert annotations.destructive_hint is False
    assert annotations.idempotent_hint is True
    assert annotations.open_world_hint is True


async def test_opened_triggers_the_browser_and_hides_the_url(browser):
    result = await _call("open_wallet_setup")

    assert result.is_error is False
    content = result.structured_content
    assert content["status"] == "opened"
    assert "setup_url" not in content
    assert "token" not in json.dumps(content).lower()
    assert len(browser) == 1
    assert browser[0].startswith("http://127.0.0.1:")
    assert "never" in content["message"] and "conversation" in content["message"]


async def test_a_second_call_reuses_the_same_page(browser):
    first = await _call("open_wallet_setup")
    second = await _call("open_wallet_setup")

    assert first.structured_content["status"] == "opened"
    assert second.structured_content["status"] == "already_open"
    assert "setup_url" not in second.structured_content
    assert len(browser) == 2
    assert browser[0] == browser[1]


@pytest.mark.parametrize("failure", ["returns_false", "raises"])
async def test_open_manually_when_the_browser_cannot_be_opened(monkeypatch, failure):
    def fake_open(url, *args, **kwargs):
        if failure == "raises":
            raise webbrowser.Error("no runnable browser")
        return False

    monkeypatch.setattr(webbrowser, "open", fake_open)

    result = await _call("open_wallet_setup")

    content = result.structured_content
    assert result.is_error is False
    assert content["status"] == "open_manually"
    assert content["setup_url"].startswith("http://127.0.0.1:")
    assert content["setup_url"] == setup_page.current_session().url
    assert content["terminal_alternative"] == "mcp-investidor10-wallet configure"
    assert "10 minutes" in content["message"]


async def test_setup_unavailable_when_the_local_port_cannot_open(monkeypatch, browser):
    def refuse(*args, **kwargs):
        raise OSError("address not available")

    monkeypatch.setattr(setup_page, "_make_server", refuse)

    result = await _call("open_wallet_setup")

    assert result.is_error is True
    error = result.structured_content["error"]
    assert error["code"] == "setup_unavailable"
    assert "mcp-investidor10-wallet configure" in error["message"]
    assert "Do not ask for the wallet link in this conversation" in error["message"]
    assert browser == []


def _configure(home):
    wallet_config.write_config(
        home,
        wallet_config.LocalConfig(
            wallet_id=WALLET,
            share_hash=CREDENTIAL,
            mode="restricted",
            mask_values=False,
            validated_at="2026-11-06T10:00:00-03:00",
            source="setup_page",
        ),
    )


@respx.mock
async def test_no_tool_response_carries_the_wallet_the_credential_or_the_link(
    browser, isolated_home, monkeypatch
):
    monkeypatch.delenv("WALLET_ID", raising=False)
    _configure(isolated_home)
    respx.get(f"{PROXY}/summary/metrics/{WALLET}").respond(
        json={"applied": 10, "equity": 11}
    )
    respx.get(f"{PROXY}/summary/donutchart/{WALLET}/all").mock(
        side_effect=httpx.ConnectError(
            f"cannot reach {PROXY}/summary/donutchart/{WALLET}/all?hash={CREDENTIAL}"
        )
    )
    respx.get(f"{PROXY}/summary/actives/{WALLET}/Ticker").respond(status_code=301)
    respx.get(f"{PROXY}/summary/barchart/{WALLET}/12/all").respond(status_code=404)
    respx.get(url__startswith=f"{PROXY}/earnings/total-period/{WALLET}").respond(
        status_code=500
    )

    calls = [
        ("open_wallet_setup", {}),
        ("get_session_context", {}),
        ("get_wallet_summary", {}),
        ("get_wallet_allocation", {}),
        ("get_wallet_positions", {"asset_type": "Ticker"}),
        ("get_patrimony_history", {"months": 12}),
        ("get_earnings", {}),
    ]
    for tool, arguments in calls:
        result = await _call(tool, arguments)
        text = json.dumps(result.structured_content) + "".join(
            getattr(block, "text", "") for block in result.content
        )
        assert WALLET not in text, tool
        assert CREDENTIAL not in text, tool
        assert "wallet/public" not in text, tool
        assert "?h=" not in text, tool
