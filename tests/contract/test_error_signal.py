import errno
import json

import filelock
import pytest
import respx
from fastmcp import Client

from investidor10_wallet import privacy, server, wallet_client, wallet_config
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


def _configure(home, wallet_id, share_hash=None, mask_values=False):
    wallet_config.write_config(
        home,
        wallet_config.LocalConfig(
            wallet_id=wallet_id,
            share_hash=share_hash,
            mode="restricted" if share_hash else "public",
            mask_values=mask_values,
            validated_at="2026-11-06T10:00:00-03:00",
            source="configure",
        ),
    )


async def _call(tool, arguments=None):
    async with Client(mcp) as client:
        return await client.call_tool(tool, arguments or {}, raise_on_error=False)


def _assert_error(result, code):
    assert result.is_error is True
    assert result.structured_content["error"]["code"] == code
    text = result.content[0].text
    assert code in text
    message = result.structured_content["error"]["message"]
    assert json.loads(text)["error"]["message"] == message
    return message


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


@respx.mock
async def test_access_denied_is_provoked_by_a_real_301_from_the_proxy():
    respx.get(SUMMARY).respond(
        status_code=301, headers={"content-type": "text/html; charset=UTF-8"}
    )
    result = await _call("get_wallet_summary")
    message = _assert_error(result, "access_denied")
    assert "open_wallet_setup" in message
    assert "Retrying will not help" in message
    assert wallet_client.WALLET_ID not in result.content[0].text
    assert "hash=" not in result.content[0].text
    assert "http" not in message


@respx.mock
async def test_access_denied_message_does_not_carry_the_credential(isolated_home):
    credential = "Zx9_credential-Q7"
    _configure(isolated_home, wallet_client.WALLET_ID, credential)
    route = respx.get(SUMMARY).respond(status_code=301)
    result = await _call("get_wallet_summary")
    _assert_error(result, "access_denied")
    assert route.calls.last.request.url.params["hash"] == credential
    assert credential not in result.content[0].text


@respx.mock
async def test_a_4xx_source_unavailable_hint_names_the_setup_tool_not_wallet_id():
    respx.get(SUMMARY).respond(status_code=404)
    message = _assert_error(await _call("get_wallet_summary"), "source_unavailable")
    assert "open_wallet_setup" in message
    assert "WALLET_ID" not in message


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


WALLET_TOOLS = [
    ("get_wallet_summary", {}),
    ("get_wallet_allocation", {}),
    ("get_wallet_positions", {"asset_type": "Ticker"}),
    ("get_patrimony_history", {"months": 12}),
    ("get_earnings", {}),
]


@pytest.fixture
def pending(monkeypatch):
    monkeypatch.delenv("WALLET_ID", raising=False)


@pytest.mark.parametrize(
    ("tool", "arguments"), WALLET_TOOLS, ids=[t for t, _ in WALLET_TOOLS]
)
@respx.mock
async def test_wallet_not_configured_for_every_wallet_tool_without_http(
    pending, tool, arguments
):
    result = await _call(tool, arguments)
    message = _assert_error(result, "wallet_not_configured")
    assert "open_wallet_setup" in message
    assert "not in this conversation" in message
    assert respx.calls.call_count == 0


@pytest.mark.parametrize(
    ("tool", "arguments"), WALLET_TOOLS, ids=[t for t, _ in WALLET_TOOLS]
)
@respx.mock
async def test_wallet_not_configured_wins_over_privacy_mode(
    pending, tool, arguments, monkeypatch
):
    monkeypatch.setenv("WALLET_MASK_VALUES", "1")
    _assert_error(await _call(tool, arguments), "wallet_not_configured")
    assert respx.calls.call_count == 0


async def test_memory_tools_keep_working_without_a_wallet(pending, memory):
    memory.save_rule("no more than 10% per asset")
    result = await _call("get_rules")
    assert result.is_error is False
    assert result.structured_content["rules"][0]["text"] == (
        "no more than 10% per asset"
    )


@respx.mock
async def test_quotes_keep_working_without_a_wallet(pending):
    respx.get(f"{REST}/assets/tickers/PETR4").respond(
        json={"variation_day": {"last_quotation": 34.2}}
    )
    result = await _call("get_asset_quote", {"ticker": "PETR4"})
    assert result.is_error is False
    assert result.structured_content["data"]["variation_day"]["last_quotation"] == 34.2


@respx.mock
async def test_a_wallet_saved_while_running_is_used_on_the_next_call(
    pending, isolated_home
):
    _assert_error(await _call("get_wallet_summary"), "wallet_not_configured")
    _configure(isolated_home, "7654321", "Zx9_credential-Q7")
    route = respx.get(f"{PROXY}/summary/metrics/7654321").respond(
        json={"applied": 1, "equity": 2}
    )

    result = await _call("get_wallet_summary")

    assert result.is_error is False
    assert route.calls.last.request.url.params["hash"] == "Zx9_credential-Q7"
