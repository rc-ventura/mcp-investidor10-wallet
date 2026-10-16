"""Live integration tests against the real Investidor10 API (opt-in).

These hit investidor10.com.br and are excluded from the default pytest run
(see addopts in pyproject.toml). Run explicitly with:

    uv run pytest -m live
"""

import pytest
from fastmcp import Client

from server import mcp

pytestmark = pytest.mark.live


async def test_live_wallet_summary_returns_data():
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_summary", {})
    payload = result.data
    assert "error" not in payload, payload
    assert payload["data"], "summary payload should not be empty"


async def test_live_all_asset_classes_respond_without_error():
    async with Client(mcp) as client:
        for asset_type in ("Ticker", "Fii", "EtfInternational", "Treasure", "Crypto"):
            result = await client.call_tool("get_wallet_positions", {"asset_type": asset_type})
            payload = result.data
            assert "error" not in payload, f"{asset_type}: {payload}"


async def test_live_asset_quote_returns_positive_price():
    async with Client(mcp) as client:
        result = await client.call_tool("get_asset_quote", {"ticker": "PETR4"})
    payload = result.data
    assert "error" not in payload, payload
    last = float(payload["data"]["variation_day"]["last_quotation"])
    assert last > 0
