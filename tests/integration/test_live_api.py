"""Live integration tests against the real Investidor10 API (opt-in).

These hit investidor10.com.br and are excluded from the default pytest run
(see addopts in pyproject.toml). They need a real public wallet, passed
explicitly (the suite default is a placeholder):

    WALLET_ID=<id> uv run pytest -m live
"""

import os

import pytest
from fastmcp import Client as _Client

from investidor10_wallet import bootstrap, wallet_client
from investidor10_wallet.server import mcp


class Client(_Client):
    async def call_tool(self, name, arguments=None, **kwargs):
        kwargs.setdefault("raise_on_error", False)
        result = await super().call_tool(name, arguments, **kwargs)
        if result.is_error and result.data is None:
            result.data = result.structured_content
        return result


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("WALLET_ID") == "1234567",
        reason="live tests need a real public wallet: WALLET_ID=<id> uv run pytest -m live",
    ),
]


async def test_live_wallet_summary_returns_data():
    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_summary", {})
    payload = result.data
    assert "error" not in payload, payload
    assert payload["data"], "summary payload should not be empty"


async def test_live_all_asset_classes_respond_without_error():
    async with Client(mcp) as client:
        for asset_type in ("Ticker", "Fii", "EtfInternational", "Treasure", "Crypto"):
            result = await client.call_tool(
                "get_wallet_positions", {"asset_type": asset_type}
            )
            payload = result.data
            assert "error" not in payload, f"{asset_type}: {payload}"


async def test_live_asset_quote_returns_positive_price():
    async with Client(mcp) as client:
        result = await client.call_tool("get_asset_quote", {"ticker": "PETR4"})
    payload = result.data
    assert "error" not in payload, payload
    last = float(payload["data"]["variation_day"]["last_quotation"])
    assert last > 0


async def test_live_probe_classifies_missing_wallet_as_404():
    with pytest.raises(SystemExit) as excinfo:
        await wallet_client.validate_wallet("99999999999")
    message = str(excinfo.value)
    assert bootstrap.WALLET_NOT_FOUND_MESSAGE.format(wallet_id="99999999999") == message


async def test_live_probe_accepts_configured_wallet():
    await wallet_client.validate_wallet(wallet_client.WALLET_ID)
