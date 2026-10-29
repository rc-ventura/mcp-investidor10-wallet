import errno
import json

import filelock
import pytest
import respx
from fastmcp import Client

from investidor10_wallet import privacy, server, wallet_client
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

PROXY = wallet_client.WALLET_PROXY_BASE_URL
REST = wallet_client.REST_BASE_URL
SUMMARY = f"{PROXY}/summary/metrics/{wallet_client.WALLET_ID}"


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


def _assert_error(result, code):
    assert result.is_error is True
    assert result.structured_content["error"]["code"] == code
    text = result.content[0].text
    assert code in text
    assert result.structured_content["error"]["message"] in text
    return result.structured_content["error"]["message"]


@respx.mock
async def test_source_unavailable_is_an_error_with_a_next_action():
    respx.get(SUMMARY).respond(status_code=500)
    message = _assert_error(await _call("get_wallet_summary"), "source_unavailable")
    assert "Retry" in message


@respx.mock
async def test_unexpected_format_is_an_error_that_forbids_using_the_numbers():
    respx.get(SUMMARY).respond(json={})
    message = _assert_error(await _call("get_wallet_summary"), "unexpected_format")
    assert "do not use" in message.lower()


async def test_invalid_asset_type_is_an_error_listing_valid_types():
    result = await _call("get_wallet_positions", {"asset_type": "Foo"})
    message = _assert_error(result, "invalid_asset_type")
    assert "Ticker" in message and "Fii" in message


@respx.mock
async def test_ticker_not_found_is_an_error():
    respx.get(f"{REST}/assets/tickers/ZZZZ9").respond(status_code=404)
    message = _assert_error(
        await _call("get_asset_quote", {"ticker": "ZZZZ9"}), "ticker_not_found"
    )
    assert "spelling" in message


@respx.mock
async def test_asset_type_not_supported_points_to_positions_tool():
    respx.get(f"{REST}/assets/tickers/MXRF11").respond(status_code=410)
    message = _assert_error(
        await _call("get_asset_quote", {"ticker": "MXRF11"}), "asset_type_not_supported"
    )
    assert "get_wallet_positions" in message


async def test_invalid_params_from_the_framework_names_the_tool():
    result = await _call("get_patrimony_history", {"months": "abc"})
    message = _assert_error(result, "invalid_params")
    assert "get_patrimony_history" in message


async def test_invalid_params_from_the_framework_names_the_argument_not_its_value():
    result = await _call("get_patrimony_history", {"months": "abc"})
    message = _assert_error(result, "invalid_params")
    assert "(months)" in message
    assert "abc" not in message


async def test_cancelling_an_inactive_alert_is_a_state_conflict(memory):
    alert = memory.create_price_alert("PETR4", "below", 30.0)
    memory.cancel_price_alert(alert["id"])
    result = await _call("cancel_price_alert", {"alert_id": alert["id"]})
    message = _assert_error(result, "state_conflict")
    assert "list_price_alerts" in message


async def test_invalid_params_from_the_domain_is_an_error():
    _assert_error(await _call("get_patrimony_history", {"months": 0}), "invalid_params")


async def test_memory_unavailable_is_an_error_that_says_to_continue_without_memory(
    tmp_path, monkeypatch
):
    path = tmp_path / "memory.json"
    path.write_text("{broken")
    monkeypatch.setattr(server, "memory", MemoryStore(str(path)))
    message = _assert_error(await _call("get_rules"), "memory_unavailable")
    assert "without" in message.lower()


async def test_not_found_for_an_alert_points_to_list_price_alerts(memory):
    message = _assert_error(
        await _call("cancel_price_alert", {"alert_id": 999}), "not_found"
    )
    assert "list_price_alerts" in message


async def test_not_found_for_a_decision_points_to_get_session_context(memory):
    result = await _call(
        "record_decision_outcome", {"decision_id": 999, "outcome": "accepted"}
    )
    message = _assert_error(result, "not_found")
    assert "get_session_context" in message


async def test_memory_busy_is_an_error_that_says_to_retry(tmp_path, monkeypatch):
    path = str(tmp_path / "memory.json")
    monkeypatch.setattr(server, "memory", MemoryStore(path, lock_timeout=0.2))
    with filelock.FileLock(f"{path}.lock"):
        result = await _call("save_rule", {"text": "r"})
    message = _assert_error(result, "memory_busy")
    assert "Retry" in message


async def test_memory_read_only_is_an_error_naming_the_fix(tmp_path, monkeypatch):
    def refuse(self, *args, **kwargs):
        raise OSError(errno.ENOSYS, "Function not implemented")

    monkeypatch.setattr(filelock.FileLock, "acquire", refuse)
    monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))
    message = _assert_error(await _call("save_rule", {"text": "r"}), "memory_read_only")
    assert "WALLET_MEMORY_PATH" in message


@respx.mock
async def test_successful_responses_carry_no_error_signal():
    payload = {"applied": "1000.5", "equity": "1100.2"}
    respx.get(SUMMARY).respond(json=payload)
    result = await _call("get_wallet_summary")
    assert result.is_error is False
    assert set(result.structured_content) == {"cached", "fetched_at", "data"}
    assert result.structured_content["data"] == payload
    assert json.loads(result.content[0].text)["data"] == payload


async def test_successful_memory_tool_carries_no_error_signal(memory):
    result = await _call("save_rule", {"text": "regra"})
    assert result.is_error is False
    assert result.structured_content["text"] == "regra"


async def test_privacy_mode_unavailable_is_an_error_naming_the_alternatives():
    privacy.configure({"mask_values": True})
    try:
        result = await _call("get_patrimony_history", {"months": 12})
    finally:
        privacy.configure({"mask_values": False})
    message = _assert_error(result, "privacy_mode_unavailable")
    assert "get_wallet_allocation" in message


async def test_unexpected_exception_is_sanitized_for_the_client_and_logged_on_the_server(
    monkeypatch, capfd
):
    async def boom():
        raise RuntimeError("secret-internal-detail")

    monkeypatch.setattr(wallet_client.wallet_client, "get_summary", boom)

    result = await _call("get_wallet_summary")

    assert result.is_error is True
    text = result.content[0].text
    assert "secret-internal-detail" not in text
    assert "get_wallet_summary" in text
    assert "secret-internal-detail" in capfd.readouterr().err
