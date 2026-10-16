"""Contract tests for the wallet data MCP tools (US1).

Tools are invoked through FastMCP's in-memory client; the Investidor10 API is
fully mocked with respx. These tests pin the response contracts specified in
specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md.
"""

import httpx
import pytest
import respx
from fastmcp import Client

import server
import wallet_client
from memory_store import MemoryStore
from server import mcp

PROXY = wallet_client.WALLET_PROXY_BASE_URL

SUMMARY_PAYLOAD = {
    "applied": 52000.0,
    "equity": 61500.5,
    "variation_total": 18.3,
    "twr_total": 0.18,
    "twr_12m": 0.11,
}
ALLOCATION_PAYLOAD = [
    {"symbol": "PETR4", "percent": 15.2},
    {"symbol": "MXRF11", "percent": 8.1},
]
POSITIONS_PAYLOAD = [
    {
        "ticker": "PETR4",
        "quantity": 100,
        "average_price": 30.5,
        "price": 34.2,
        "equity_total": 3420.0,
        "percent_wallet": 15.2,
        "percent_ideal": 8.0,
        "buy": True,
    }
]


@pytest.fixture(autouse=True)
def clear_caches():
    """Each test must see a cold cache (the module-level clients persist it)."""
    wallet_client.wallet_client._cache.clear()
    wallet_client.rest_client._cache.clear()
    yield
    wallet_client.wallet_client._cache.clear()
    wallet_client.rest_client._cache.clear()


@respx.mock
async def test_get_wallet_summary_returns_data_envelope():
    respx.get(f"{PROXY}/summary/metrics/1234567").respond(json=SUMMARY_PAYLOAD)
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_summary", {})
    payload = result.data
    assert {"cached", "fetched_at", "data"} <= set(payload)
    assert payload["cached"] is False
    assert payload["data"] == SUMMARY_PAYLOAD


@respx.mock
async def test_get_wallet_allocation_returns_data_envelope():
    respx.get(f"{PROXY}/summary/donutchart/1234567/all").respond(json=ALLOCATION_PAYLOAD)
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_allocation", {})
    payload = result.data
    assert payload["data"] == ALLOCATION_PAYLOAD


@respx.mock
async def test_get_wallet_positions_passthrough_keeps_percent_and_buy_fields():
    respx.get(f"{PROXY}/summary/actives/1234567/Ticker").respond(json=POSITIONS_PAYLOAD)
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_positions", {"asset_type": "Ticker"})
    payload = result.data
    position = payload["data"][0]
    for field in ("average_price", "percent_wallet", "percent_ideal", "buy"):
        assert field in position


@respx.mock
async def test_every_position_keeps_rebalancing_fields():
    """T018/US2 — the passthrough must never strip percent_wallet, percent_ideal
    or buy from ANY position, otherwise rebalancing analysis breaks (SC-003)."""
    many_positions = [
        dict(POSITIONS_PAYLOAD[0], ticker="PETR4"),
        dict(POSITIONS_PAYLOAD[0], ticker="VALE3"),
        dict(POSITIONS_PAYLOAD[0], ticker="ITUB4"),
    ]
    respx.get(f"{PROXY}/summary/actives/1234567/Ticker").respond(json=many_positions)
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_positions", {"asset_type": "Ticker"})
    for position in result.data["data"]:
        for field in ("percent_wallet", "percent_ideal", "buy"):
            assert field in position, f"field {field} stripped from {position['ticker']}"


@respx.mock
async def test_get_wallet_positions_rejects_invalid_asset_type():
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_positions", {"asset_type": "Bitcoin"})
    payload = result.data
    assert payload["error"]["code"] == "invalid_asset_type"
    message = payload["error"]["message"]
    for valid in ("Ticker", "Fii", "EtfInternational", "Treasure", "Crypto"):
        assert valid in message


@respx.mock
async def test_get_wallet_positions_accepts_normalized_case_and_empty_class():
    respx.get(f"{PROXY}/summary/actives/1234567/Fii").respond(json=[])
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_positions", {"asset_type": "fii"})
    payload = result.data
    assert "error" not in payload
    assert payload["data"] == []


@respx.mock
async def test_tool_returns_structured_error_on_source_failure():
    respx.get(f"{PROXY}/summary/metrics/1234567").respond(status_code=500)
    wallet_client.wallet_client._cache.clear()
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_summary", {})
    payload = result.data
    assert payload["error"]["code"] == "source_unavailable"


class TestGetAssetQuote:
    """T026/US4 — contract of the quote tool against the REST assets API."""

    QUOTE_PAYLOAD = {
        "variation_day": {"last_quotation": "57.45", "variation_percent": 1.2},
        "variation_twelve": 103.7,
        "dy": "6,23",
        "graham": {"price": "93.21"},
        "bazin": {"price": "137.13"},
        "sector": {"segment": {"name": "Exploração, Refino e Distribuição"}},
    }

    async def test_quote_returns_data_envelope(self):
        with respx.mock:
            respx.get(f"{wallet_client.REST_BASE_URL}/assets/tickers/PETR4").respond(
                json=self.QUOTE_PAYLOAD
            )
            wallet_client.rest_client._cache.clear()
            async with Client(mcp) as client:
                result = await client.call_tool("get_asset_quote", {"ticker": "PETR4"})
        payload = result.data
        assert {"cached", "fetched_at", "data"} <= set(payload)
        assert payload["data"] == self.QUOTE_PAYLOAD

    async def test_quote_normalizes_ticker(self):
        route = None
        with respx.mock:
            route = respx.get(f"{wallet_client.REST_BASE_URL}/assets/tickers/PETR4").respond(
                json=self.QUOTE_PAYLOAD
            )
            wallet_client.rest_client._cache.clear()
            async with Client(mcp) as client:
                await client.call_tool("get_asset_quote", {"ticker": " petr4 "})
        assert route.called, "the request must hit the normalized PETR4 endpoint"

    async def test_unknown_ticker_returns_ticker_not_found(self):
        with respx.mock:
            respx.get(f"{wallet_client.REST_BASE_URL}/assets/tickers/VALE99").respond(status_code=404)
            wallet_client.rest_client._cache.clear()
            async with Client(mcp) as client:
                result = await client.call_tool("get_asset_quote", {"ticker": "VALE99"})
        payload = result.data
        assert payload["error"]["code"] == "ticker_not_found"
        assert "spelling" in payload["error"]["message"].lower()


class TestGetSessionContext:
    """T022 — contract of the session bootstrap tool and memory error mapping."""

    async def test_returns_digest_shape_with_fresh_memory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))
        async with Client(mcp) as client:
            result = await client.call_tool("get_session_context", {})
        payload = result.data
        assert payload["memory_status"] == "ok"
        assert payload["triggered_alerts"] == []
        digest = payload["memory"]
        assert set(digest) >= {"wallet_goal", "theses", "rules", "pending_decisions", "recent_insights"}

    async def test_invalid_params_and_not_found_mapping(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))
        async with Client(mcp) as client:
            bad_kind = (await client.call_tool("log_decision", {"kind": "nonsense", "content": "x"})).data
            assert bad_kind["error"]["code"] == "invalid_params"
            missing = (
                await client.call_tool("record_decision_outcome", {"decision_id": 999, "outcome": "accepted"})
            ).data
            assert missing["error"]["code"] == "not_found"

    async def test_corrupted_memory_reports_unavailable_and_data_tools_still_work(
        self, tmp_path, monkeypatch
    ):
        broken = tmp_path / "memory.json"
        broken.write_text("{corrupt", encoding="utf-8")
        monkeypatch.setattr(server, "memory", MemoryStore(str(broken)))

        async with Client(mcp) as client:
            context = (await client.call_tool("get_session_context", {})).data
            assert context["memory_status"] == "unavailable"
            assert context["memory"] is None

            save = (await client.call_tool("save_thesis", {"ticker": "PETR4", "text": "x"})).data
            assert save["error"]["code"] == "memory_unavailable"

            # Data tools keep working while memory is down (spec edge case).
            with respx.mock:
                respx.get(f"{PROXY}/summary/metrics/1234567").respond(json=SUMMARY_PAYLOAD)
                wallet_client.wallet_client._cache.clear()
                summary = (await client.call_tool("get_wallet_summary", {})).data
            assert summary["data"] == SUMMARY_PAYLOAD
