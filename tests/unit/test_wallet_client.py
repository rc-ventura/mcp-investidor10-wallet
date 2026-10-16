"""Unit tests for the Investidor10 wallet HTTP client: TTL cache and error handling.

The API is fully mocked with respx; no network access happens here.
"""

import time

import httpx
import pytest
import respx

import wallet_client
from wallet_client import SourceError, WalletClient

BASE = "https://api.example.test"
PATH = "/summary/metrics/2061045"
PAYLOAD = {"applied": 1000.0, "equity": 1150.0}


def make_client(**kwargs) -> WalletClient:
    return WalletClient(BASE, **kwargs)


@respx.mock
async def test_cache_hit_within_ttl_avoids_second_request():
    route = respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json=PAYLOAD))
    client = make_client(ttl_seconds=600)

    first = await client.request(PATH)
    second = await client.request(PATH)

    assert route.call_count == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["data"] == PAYLOAD
    assert second["fetched_at"] == first["fetched_at"]


@respx.mock
async def test_cache_entry_expires_after_ttl():
    route = respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json=PAYLOAD))
    client = make_client(ttl_seconds=600)

    await client.request(PATH)
    # Force the cached entry to be older than the TTL.
    cache_key = (BASE, PATH, tuple())
    _, fetched_at, data = client._cache[cache_key]
    client._cache[cache_key] = (time.monotonic() - 9999, fetched_at, data)

    second = await client.request(PATH)
    assert route.call_count == 2
    assert second["cached"] is False


@respx.mock
async def test_timeout_without_cache_raises_source_unavailable():
    respx.get(f"{BASE}{PATH}").mock(side_effect=httpx.ConnectTimeout("boom"))
    client = make_client()

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH)
    assert excinfo.value.code == "source_unavailable"


@respx.mock
async def test_http_500_raises_source_unavailable():
    respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(500))
    client = make_client()

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH)
    assert excinfo.value.code == "source_unavailable"
    assert "500" in excinfo.value.message


@respx.mock
async def test_non_json_body_raises_unexpected_format():
    respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, content=b"<html>surprise</html>"))
    client = make_client()

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH)
    assert excinfo.value.code == "unexpected_format"


@respx.mock
async def test_source_failure_serves_stale_cache_with_explicit_age():
    route = respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json=PAYLOAD))
    client = make_client(ttl_seconds=600)

    first = await client.request(PATH)
    # Expire the entry in the client cache, then make the source fail.
    cache_key = (BASE, PATH, tuple())
    _, fetched_at, data = client._cache[cache_key]
    client._cache[cache_key] = (time.monotonic() - 9999, fetched_at, data)
    route.mock(side_effect=httpx.ConnectTimeout("boom"))

    stale = await client.request(PATH)
    assert stale["cached"] is True
    assert stale["data"] == PAYLOAD
    assert stale["fetched_at"] == first["fetched_at"]


@respx.mock
async def test_required_keys_missing_raises_unexpected_format():
    respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json={"applied": 1}))
    client = make_client()

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH, required_keys=["applied", "equity"])
    assert excinfo.value.code == "unexpected_format"


def test_default_clients_use_configured_bases():
    assert wallet_client.wallet_client.base_url == wallet_client.WALLET_PROXY_BASE_URL
    assert wallet_client.rest_client.base_url == wallet_client.REST_BASE_URL


def test_to_payload_shape():
    err = SourceError("unexpected_format", "bad body")
    assert err.to_payload() == {"error": {"code": "unexpected_format", "message": "bad body"}}
