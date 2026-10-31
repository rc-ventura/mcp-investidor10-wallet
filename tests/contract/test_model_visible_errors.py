"""What a tool returns to the model on failure: no wallet ID, no crash on hostile JSON."""

import pytest
import respx
from fastmcp import Client

from investidor10_wallet import server, wallet_client
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

PROXY = wallet_client.WALLET_PROXY_BASE_URL
REST = wallet_client.REST_BASE_URL
WALLET = wallet_client.WALLET_ID
SUMMARY = f"{PROXY}/summary/metrics/{WALLET}"
DEEP = b"[" * 100_000 + b"]" * 100_000


@pytest.fixture(autouse=True)
def clear_caches():
    wallet_client.wallet_client._cache.clear()
    wallet_client.rest_client._cache.clear()
    yield
    wallet_client.wallet_client._cache.clear()
    wallet_client.rest_client._cache.clear()


@pytest.fixture
def memory(tmp_path, monkeypatch):
    store = MemoryStore(str(tmp_path / "memory.json"))
    monkeypatch.setattr(server, "memory", store)
    return store


async def _call(tool, arguments=None):
    async with Client(mcp) as client:
        return await client.call_tool(tool, arguments or {}, raise_on_error=False)


def _everything_the_model_sees(result) -> str:
    return result.content[0].text + repr(result.structured_content)


def test_the_test_wallet_id_is_configured():
    assert WALLET


@pytest.mark.parametrize(
    "mock",
    [
        {"status_code": 404},
        {"status_code": 500},
        {"content": b"not json"},
        {"json": {}},
    ],
    ids=["http_404", "http_500", "non_json", "missing_keys"],
)
@respx.mock
async def test_summary_failure_never_shows_the_wallet_id_to_the_model(mock):
    respx.get(SUMMARY).respond(**mock)

    result = await _call("get_wallet_summary")

    assert result.is_error is True
    assert WALLET not in _everything_the_model_sees(result)


@respx.mock
async def test_a_deeply_nested_summary_is_an_unexpected_format_error():
    respx.get(SUMMARY).respond(content=DEEP)

    result = await _call("get_wallet_summary")

    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "unexpected_format"
    assert WALLET not in _everything_the_model_sees(result)


@respx.mock
async def test_a_deeply_nested_quote_is_an_unexpected_format_error():
    respx.get(f"{REST}/assets/tickers/PETR4").respond(content=DEEP)

    result = await _call("get_asset_quote", {"ticker": "PETR4"})

    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "unexpected_format"


@respx.mock
async def test_session_context_survives_a_hostile_quote_and_still_returns_memory(
    memory,
):
    memory.save_rule("never average down")
    memory.create_price_alert("PETR4", "below", 999.0)
    respx.get(f"{REST}/assets/tickers/PETR4").respond(content=DEEP)

    result = await _call("get_session_context")

    assert result.is_error is False
    payload = result.structured_content
    assert payload["memory_status"] == "ok"
    assert payload["pending_check"] == [
        {"ticker": "PETR4", "reason": "unexpected_format"}
    ]
    assert [r["text"] for r in payload["memory"]["rules"]] == ["never average down"]
    assert len(memory.list_price_alerts("active")) == 1
