import json
from pathlib import Path

import pytest
import respx
from fastmcp import Client

from investidor10_wallet import privacy, server, wallet_client
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "privacy"
PROXY = wallet_client.WALLET_PROXY_BASE_URL
REST = wallet_client.REST_BASE_URL
WALLET = wallet_client.WALLET_ID
SENTINEL = "9988.77"
CLASSES = ("Ticker", "Fii", "EtfInternational", "Treasure", "Crypto")
MASKED_TOOLS = ("get_wallet_summary", "get_wallet_allocation", "get_wallet_positions")
BLOCKED_TOOLS = ("get_patrimony_history", "get_earnings")


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def clear_caches():
    wallet_client.wallet_client._cache.clear()
    wallet_client.rest_client._cache.clear()
    yield
    wallet_client.wallet_client._cache.clear()
    wallet_client.rest_client._cache.clear()
    privacy.configure({"mask_values": False})


@pytest.fixture
def masked():
    privacy.configure({"mask_values": True})


async def _call(tool, arguments=None):
    async with Client(mcp) as client:
        return await client.call_tool(tool, arguments or {}, raise_on_error=False)


def _serialized(result):
    return json.dumps(result.structured_content) + result.content[0].text


@respx.mock
async def test_summary_withholds_amounts_and_reports_what_was_omitted(masked):
    respx.get(f"{PROXY}/summary/metrics/{WALLET}").respond(json=_load("summary.json"))
    result = await _call("get_wallet_summary")
    assert result.is_error is False
    assert SENTINEL not in _serialized(result)
    sc = result.structured_content
    assert sc["privacy"]["masked"] is True
    assert set(sc["privacy"]["omitted"]) == {
        "applied",
        "equity",
        "profit_amount",
        "profit_twr_12m_amount",
    }
    assert sc["data"]["variation"] == "12.34"


@respx.mock
async def test_allocation_keeps_percentages_only(masked):
    respx.get(f"{PROXY}/summary/donutchart/{WALLET}/all").respond(
        json=_load("allocation.json")
    )
    result = await _call("get_wallet_allocation")
    assert SENTINEL not in _serialized(result)
    assert [item["percent"] for item in result.structured_content["data"]] == [
        15.2,
        40.1,
    ]


@pytest.mark.parametrize("asset_class", CLASSES)
@respx.mock
async def test_positions_of_every_class_have_no_amounts_or_quantities(
    masked, asset_class
):
    respx.get(f"{PROXY}/summary/actives/{WALLET}/{asset_class}").respond(
        json=_load(f"positions_{asset_class}.json")
    )
    result = await _call("get_wallet_positions", {"asset_type": asset_class})
    assert result.is_error is False
    assert SENTINEL not in _serialized(result)
    row = result.structured_content["data"]["data"][0]
    assert row["percent_wallet"] == 15.2
    assert "quantity" not in row and "equity_total" not in row


@pytest.mark.parametrize(
    "tool,arguments,route",
    [
        (
            "get_patrimony_history",
            {"months": 12},
            f"{PROXY}/summary/barchart/{WALLET}/12/all",
        ),
        ("get_earnings", {}, f"{PROXY}/earnings/total-period/{WALLET}"),
    ],
)
async def test_monetary_tools_are_unavailable_without_calling_the_source(
    masked, tool, arguments, route
):
    with respx.mock(assert_all_called=False) as router:
        source = router.get(url__regex=r".*").respond(json={"sum": 1})
        result = await _call(tool, arguments)
    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "privacy_mode_unavailable"
    assert tool in result.structured_content["error"]["message"]
    assert source.call_count == 0


async def test_earnings_with_inverted_dates_is_still_invalid_params(masked):
    result = await _call(
        "get_earnings", {"start_date": "2026-10-10", "end_date": "2026-01-01"}
    )
    assert result.structured_content["error"]["code"] == "invalid_params"


@respx.mock
async def test_asset_quote_is_not_affected(masked):
    quote = {"variation_day": {"last_quotation": "34.20"}, "name": "Petrobras"}
    respx.get(f"{REST}/assets/tickers/PETR4").respond(json=quote)
    result = await _call("get_asset_quote", {"ticker": "PETR4"})
    assert result.structured_content["data"] == quote
    assert "privacy" not in result.structured_content


async def test_memory_tools_are_not_affected(masked, tmp_path, monkeypatch):
    monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))
    result = await _call("save_rule", {"text": "gastar até R$ 5000 por mês"})
    assert result.structured_content["text"] == "gastar até R$ 5000 por mês"


@respx.mock
async def test_mode_off_returns_the_source_payload_without_a_privacy_marker():
    payload = _load("summary.json")
    respx.get(f"{PROXY}/summary/metrics/{WALLET}").respond(json=payload)
    result = await _call("get_wallet_summary")
    assert result.structured_content["data"] == payload
    assert "privacy" not in result.structured_content


@respx.mock
async def test_cached_raw_payload_is_never_served_unmasked_after_enabling_the_mode():
    respx.get(f"{PROXY}/summary/metrics/{WALLET}").respond(json=_load("summary.json"))
    first = await _call("get_wallet_summary")
    assert SENTINEL in _serialized(first)

    privacy.configure({"mask_values": True})
    second = await _call("get_wallet_summary")

    assert second.structured_content["cached"] is True
    assert SENTINEL not in _serialized(second)


async def test_tool_descriptions_tell_the_model_how_to_treat_masked_data():
    async with Client(mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    for name in MASKED_TOOLS:
        assert "privacy.masked" in tools[name].description
        assert "never estimate" in tools[name].description
    for name in BLOCKED_TOOLS:
        assert "privacy_mode_unavailable" in tools[name].description


async def test_no_tool_exposes_a_privacy_parameter_and_schemas_do_not_change():
    async with Client(mcp) as client:
        before = {t.name: t.input_schema for t in await client.list_tools()}
        privacy.configure({"mask_values": True})
        after = {t.name: t.input_schema for t in await client.list_tools()}
    assert before == after
    for schema in after.values():
        for name in schema.get("properties", {}):
            assert "privacy" not in name.lower() and "mask" not in name.lower()
