"""The wallet ID is a credential: no error text that reaches the model may carry it."""

import time

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
async def test_a_4xx_on_the_wallet_proxy_still_hints_at_wallet_id():
    respx.get(URL).mock(return_value=httpx.Response(404))

    with pytest.raises(SourceError) as excinfo:
        await make_client().request(PATH)

    assert "check WALLET_ID" in excinfo.value.message
    assert excinfo.value.status_code == 404


def test_redaction_is_exact_and_does_not_touch_longer_numbers():
    client = make_client()
    assert client._redact(f"id {WALLET} and 1{WALLET}9") == (
        f"id {wallet_client.WALLET_PLACEHOLDER} and 1{WALLET}9"
    )


def test_an_unconfigured_client_redacts_nothing():
    client = WalletClient(PROXY, wallet_id="", _allow_unconfigured=True)
    assert client._redact("GET /summary/metrics/42") == "GET /summary/metrics/42"
