"""The wallet ID is a credential: no error text that reaches the model may carry it."""

import time
from types import SimpleNamespace

import httpx
import pytest
import respx

from investidor10_wallet import wallet_client
from investidor10_wallet.wallet_client import SourceError, WalletClient

WALLET = "7654321"
PROXY = wallet_client.WALLET_PROXY_BASE_URL
PATH = f"/summary/metrics/{WALLET}"
URL = f"{PROXY}{PATH}"
DEEP = b"[" * 100_000 + b"]" * 100_000


def make_client(**kwargs) -> WalletClient:
    return WalletClient(PROXY, wallet_id=WALLET, **kwargs)


def _assert_redacted(error: SourceError):
    for text in (error.message, str(error), repr(error.to_payload())):
        assert WALLET not in text
    assert wallet_client.WALLET_PLACEHOLDER in error.message


CASES = [
    ("http_404", {"return_value": httpx.Response(404)}, {}, "source_unavailable"),
    ("http_500", {"return_value": httpx.Response(500)}, {}, "source_unavailable"),
    (
        "transport_error",
        {"side_effect": httpx.ConnectError(f"cannot reach {URL}")},
        {},
        "source_unavailable",
    ),
    (
        "non_json",
        {"return_value": httpx.Response(200, content=b"not json")},
        {},
        "unexpected_format",
    ),
    (
        "deeply_nested_json",
        {"return_value": httpx.Response(200, content=DEEP)},
        {},
        "unexpected_format",
    ),
    (
        "wrong_type",
        {"return_value": httpx.Response(200, json=[])},
        {"expected_type": dict},
        "unexpected_format",
    ),
    (
        "missing_keys",
        {"return_value": httpx.Response(200, json={})},
        {"required_keys": ["applied"]},
        "unexpected_format",
    ),
    (
        "field_type",
        {"return_value": httpx.Response(200, json={"applied": "x"})},
        {"required_types": {"applied": wallet_client.NUMERIC}},
        "unexpected_format",
    ),
]


@pytest.mark.parametrize(
    ("name", "mock", "kwargs", "code"), CASES, ids=[c[0] for c in CASES]
)
@respx.mock
async def test_error_text_never_carries_the_wallet_id(name, mock, kwargs, code):
    route = respx.get(URL).mock(**mock)

    with pytest.raises(SourceError) as excinfo:
        await make_client().request(PATH, **kwargs)

    assert excinfo.value.code == code
    _assert_redacted(excinfo.value)
    # The real request still goes to the real path.
    assert route.call_count == 1


@respx.mock
async def test_oversized_body_error_does_not_carry_the_wallet_id(monkeypatch):
    monkeypatch.setattr(wallet_client, "MAX_RESPONSE_BYTES", 10)
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"0" * 11))

    with pytest.raises(SourceError) as excinfo:
        await make_client().request(PATH)

    assert excinfo.value.code == "unexpected_format"
    _assert_redacted(excinfo.value)


@pytest.mark.parametrize("failure", ["transport_error", "http_503"])
@respx.mock
async def test_stale_refusal_error_does_not_carry_the_wallet_id(failure):
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"a": 1}))
    client = make_client(ttl_seconds=600, max_stale_seconds=60)
    await client.request(PATH)
    key = (PROXY, PATH, ())
    _, fetched_at, data = client._cache[key]
    client._cache[key] = (time.monotonic() - 3600, fetched_at, data)
    if failure == "transport_error":
        route.mock(side_effect=httpx.ConnectTimeout(f"timeout on {URL}"))
    else:
        route.mock(return_value=httpx.Response(503))

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH)

    assert excinfo.value.code == "source_unavailable"
    _assert_redacted(excinfo.value)


@respx.mock
async def test_a_4xx_on_the_wallet_proxy_points_to_the_setup_tool():
    respx.get(URL).mock(return_value=httpx.Response(404))

    with pytest.raises(SourceError) as excinfo:
        await make_client().request(PATH)

    assert "open_wallet_setup" in excinfo.value.message
    assert "WALLET_ID" not in excinfo.value.message
    assert excinfo.value.status_code == 404


def test_redaction_is_exact_and_does_not_touch_longer_numbers():
    client = make_client()
    assert client._redact(f"id {WALLET} and 1{WALLET}9") == (
        f"id {wallet_client.WALLET_PLACEHOLDER} and 1{WALLET}9"
    )


def test_an_unconfigured_client_redacts_nothing():
    client = WalletClient(PROXY, wallet_id="", _allow_unconfigured=True)
    assert client._redact("GET /summary/metrics/42") == "GET /summary/metrics/42"


HASH = "Zx9_credential-Q7"
REST = wallet_client.REST_BASE_URL


def _state(wallet_id, share_hash=None):
    return SimpleNamespace(wallet_id=wallet_id, share_hash=share_hash)


def make_restricted_client(base_url=PROXY, **kwargs) -> WalletClient:
    return WalletClient(base_url, wallet_id=WALLET, share_hash=HASH, **kwargs)


def _assert_hash_redacted(error: SourceError):
    for text in (error.message, str(error), repr(error.to_payload())):
        assert HASH not in text


@respx.mock
async def test_every_proxy_request_carries_the_hash_parameter():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"a": 1}))

    await make_restricted_client().request(PATH, params={"raw": 1})

    params = route.calls.last.request.url.params
    assert params["hash"] == HASH
    assert params["raw"] == "1"


@respx.mock
async def test_quote_requests_never_carry_the_hash_parameter():
    quote_url = f"{REST}/assets/tickers/PETR4"
    route = respx.get(quote_url).mock(return_value=httpx.Response(200, json={"a": 1}))

    await make_restricted_client(REST).request("/assets/tickers/PETR4")

    assert "hash" not in route.calls.last.request.url.params
    assert HASH not in str(route.calls.last.request.url)


@respx.mock
async def test_a_public_client_sends_no_hash_parameter():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"a": 1}))

    await make_client().request(PATH)

    assert "hash" not in route.calls.last.request.url.params


@respx.mock
async def test_the_credential_is_not_part_of_the_cache_key():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"a": 1}))
    client = make_restricted_client()

    await client.request(PATH)

    assert all(HASH not in repr(key) for key in client._cache)


@pytest.mark.parametrize(
    ("name", "mock"),
    [
        ("http_404", {"return_value": httpx.Response(404)}),
        ("http_500", {"return_value": httpx.Response(500)}),
        ("access_denied", {"return_value": httpx.Response(301)}),
        ("non_json", {"return_value": httpx.Response(200, content=b"not json")}),
        (
            "transport_error",
            {
                "side_effect": httpx.ConnectError(
                    f"cannot reach {URL}?hash={HASH}&raw=1"
                )
            },
        ),
        (
            "timeout_with_url",
            {"side_effect": httpx.ReadTimeout(f"timeout on {URL}?raw=1&hash={HASH}")},
        ),
    ],
)
@respx.mock
async def test_error_text_never_carries_the_credential(name, mock):
    respx.get(url__startswith=URL).mock(**mock)

    with pytest.raises(SourceError) as excinfo:
        await make_restricted_client().request(PATH)

    _assert_hash_redacted(excinfo.value)
    for text in (excinfo.value.message, str(excinfo.value)):
        assert WALLET not in text


@respx.mock
async def test_a_transport_error_text_shows_the_hash_placeholder():
    respx.get(url__startswith=URL).mock(
        side_effect=httpx.ConnectError(f"cannot reach {URL}?hash={HASH}")
    )

    with pytest.raises(SourceError) as excinfo:
        await make_restricted_client().request(PATH)

    assert wallet_client.HASH_PLACEHOLDER in excinfo.value.message


def test_redaction_of_the_credential_is_exact():
    client = make_restricted_client()
    assert client._redact(f"?hash={HASH}&x=1 and {HASH}9") == (
        f"?hash={wallet_client.HASH_PLACEHOLDER}&x=1 and {HASH}9"
    )


@respx.mock
async def test_apply_configuration_swaps_wallet_and_credential_on_both_clients():
    wallet, rest = wallet_client.wallet_client, wallet_client.rest_client
    wallet._cache["k"] = (time.monotonic(), "now", {"a": 1})
    rest._cache["k"] = (time.monotonic(), "now", {"b": 2})
    saved = (wallet.wallet_id, wallet.share_hash, rest.wallet_id, rest.share_hash)
    try:
        wallet_client.apply_configuration(_state("424242", HASH))

        assert (wallet.wallet_id, wallet.share_hash) == ("424242", HASH)
        assert (rest.wallet_id, rest.share_hash) == ("424242", HASH)
        assert wallet._cache == {} and rest._cache == {}
    finally:
        wallet.wallet_id, wallet.share_hash, rest.wallet_id, rest.share_hash = saved
        wallet._cache.clear()
        rest._cache.clear()


def test_apply_configuration_keeps_the_cache_when_nothing_changed():
    wallet = wallet_client.wallet_client
    saved = (wallet.wallet_id, wallet.share_hash)
    try:
        wallet_client.apply_configuration(_state("424242", HASH))
        wallet._cache["k"] = (time.monotonic(), "now", {"a": 1})

        wallet_client.apply_configuration(_state("424242", HASH))

        assert "k" in wallet._cache
    finally:
        wallet.wallet_id, wallet.share_hash = saved
        wallet_client.rest_client.wallet_id = saved[0]
        wallet_client.rest_client.share_hash = saved[1]
        wallet._cache.clear()


def test_apply_configuration_clears_the_cache_when_only_the_credential_changes():
    wallet = wallet_client.wallet_client
    saved = (wallet.wallet_id, wallet.share_hash)
    try:
        wallet_client.apply_configuration(_state("424242", HASH))
        wallet._cache["k"] = (time.monotonic(), "now", {"a": 1})

        wallet_client.apply_configuration(_state("424242", "other_credential"))

        assert wallet._cache == {}
        assert wallet.share_hash == "other_credential"
    finally:
        wallet.wallet_id, wallet.share_hash = saved
        wallet_client.rest_client.wallet_id = saved[0]
        wallet_client.rest_client.share_hash = saved[1]
        wallet._cache.clear()
