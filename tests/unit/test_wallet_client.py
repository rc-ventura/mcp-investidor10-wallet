"""Unit tests for the Investidor10 wallet HTTP client: TTL cache and error handling.

The API is fully mocked with respx; no network access happens here.
"""

import datetime
import os
import subprocess
import sys
import time
from types import SimpleNamespace

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
    assert excinfo.value.status_code == 500


@respx.mock
async def test_non_json_body_raises_unexpected_format():
    respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, content=b"<html>surprise</html>"))
    client = make_client()

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH)
    assert excinfo.value.code == "unexpected_format"


@respx.mock
async def test_source_failure_serves_stale_cache_within_max_stale():
    route = respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json=PAYLOAD))
    client = make_client(ttl_seconds=600, max_stale_seconds=7200)

    first = await client.request(PATH)
    # Expire the entry in the client cache, then make the source fail.
    cache_key = (BASE, PATH, tuple())
    _, fetched_at, data = client._cache[cache_key]
    client._cache[cache_key] = (time.monotonic() - 3600, fetched_at, data)
    route.mock(side_effect=httpx.ConnectTimeout("boom"))

    stale = await client.request(PATH)
    assert stale["cached"] is True
    assert stale["data"] == PAYLOAD
    assert stale["fetched_at"] == first["fetched_at"]


@respx.mock
async def test_http_503_serves_stale_cache_within_max_stale():
    route = respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json=PAYLOAD))
    client = make_client(ttl_seconds=600, max_stale_seconds=7200)

    first = await client.request(PATH)
    cache_key = (BASE, PATH, tuple())
    _, fetched_at, data = client._cache[cache_key]
    client._cache[cache_key] = (time.monotonic() - 3600, fetched_at, data)
    route.mock(return_value=httpx.Response(503))

    stale = await client.request(PATH)
    assert stale["cached"] is True
    assert stale["data"] == PAYLOAD
    assert stale["fetched_at"] == first["fetched_at"]


@pytest.mark.parametrize("failure", ["transport_error", "http_503"])
@respx.mock
async def test_source_failure_beyond_max_stale_raises_source_unavailable(failure):
    """The 5xx/transport fallback is bounded (ADR-0003): a cache entry older
    than WALLET_CACHE_MAX_STALE_SECONDS must never be served as data."""
    route = respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json=PAYLOAD))
    client = make_client(ttl_seconds=600, max_stale_seconds=3600)

    await client.request(PATH)
    cache_key = (BASE, PATH, tuple())
    _, fetched_at, data = client._cache[cache_key]
    client._cache[cache_key] = (time.monotonic() - 9999, fetched_at, data)
    if failure == "transport_error":
        route.mock(side_effect=httpx.ConnectTimeout("boom"))
    else:
        route.mock(return_value=httpx.Response(503))

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH)
    assert excinfo.value.code == "source_unavailable"


@respx.mock
async def test_http_503_without_cache_raises_source_unavailable():
    respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(503))
    with pytest.raises(SourceError) as excinfo:
        await make_client().request(PATH)
    assert excinfo.value.code == "source_unavailable"


@respx.mock
async def test_required_keys_missing_raises_unexpected_format():
    respx.get(f"{BASE}{PATH}").mock(return_value=httpx.Response(200, json={"applied": 1}))
    client = make_client()

    with pytest.raises(SourceError) as excinfo:
        await client.request(PATH, required_keys=["applied", "equity"])
    assert excinfo.value.code == "unexpected_format"


@respx.mock
async def test_summary_schema_drift_returns_unexpected_format():
    respx.get(f"{BASE}/summary/metrics/2061045").respond(json={"equity": 1000})
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_summary()
    assert excinfo.value.code == "unexpected_format"


@pytest.mark.parametrize("payload", [
    {"applied": "not-a-number", "equity": 1000},
    {"applied": 1000, "equity": "nan"},
    {"applied": True, "equity": 1000},
    {"applied": 1000, "equity": []},
])
@respx.mock
async def test_summary_rejects_present_but_invalid_numeric_values(payload):
    """Present-but-invalid `applied`/`equity` must fail as unexpected_format
    and never enter the cache (cycle-2 mandatory item 4, full closure)."""
    respx.get(f"{BASE}/summary/metrics/2061045").respond(json=payload)
    client = make_client()
    with pytest.raises(SourceError) as excinfo:
        await client.get_summary()
    assert excinfo.value.code == "unexpected_format"
    assert client._cache == {}


@pytest.mark.parametrize("payload", [
    {"applied": 96801.55, "equity": 108560.23},
    {"applied": "96801.5575437", "equity": "108560.232569"},  # live source shape
])
@respx.mock
async def test_summary_accepts_valid_numeric_values(payload):
    respx.get(f"{BASE}/summary/metrics/2061045").respond(json=payload)
    envelope = await make_client().get_summary()
    assert envelope["cached"] is False
    assert envelope["data"] == payload


@pytest.mark.parametrize("path,payload,method,args", [
    ("/summary/donutchart/2061045/all", {}, "get_allocation", ()),
    ("/summary/actives/2061045/Ticker", [], "get_positions", ("Ticker",)),
    ("/summary/actives/2061045/Ticker", {"total": 0, "data": None}, "get_positions", ("Ticker",)),
    ("/earnings/total-period/2061045", {}, "get_earnings", ()),
    ("/earnings/total-period/2061045", {"sum": True}, "get_earnings", ()),
    ("/summary/barchart/2061045/12/all", {}, "get_patrimony_history", (12,)),
])
@respx.mock
async def test_wallet_endpoints_reject_schema_drift(path, payload, method, args):
    respx.get(f"{BASE}{path}").respond(json=payload)
    with pytest.raises(SourceError) as excinfo:
        await getattr(make_client(), method)(*args)
    assert excinfo.value.code == "unexpected_format"


def test_default_clients_use_configured_bases():
    assert wallet_client.wallet_client.base_url == wallet_client.WALLET_PROXY_BASE_URL
    assert wallet_client.rest_client.base_url == wallet_client.REST_BASE_URL


def test_wallet_client_rejects_non_numeric_wallet_id():
    with pytest.raises(SourceError):
        WalletClient(BASE, wallet_id="ABC?raw=1#frag")


def test_env_float_rejects_non_numeric_value(monkeypatch):
    monkeypatch.setenv("WALLET_CACHE_TTL_SECONDS", "soon")
    with pytest.raises(SystemExit) as excinfo:
        wallet_client._env_float("WALLET_CACHE_TTL_SECONDS", "600")
    assert "WALLET_CACHE_TTL_SECONDS" in str(excinfo.value)


@pytest.mark.parametrize("bad", ["-5", "nan", "inf", "-inf"])
def test_env_float_rejects_negative_and_nonfinite_values(bad):
    with pytest.raises(SystemExit):
        wallet_client._env_float("WALLET_CACHE_MAX_STALE_SECONDS", bad)


@respx.mock
async def test_http_4xx_on_wallet_proxy_mentions_wallet_id():
    url = f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/2061045"
    respx.get(url).mock(return_value=httpx.Response(404))
    with pytest.raises(SourceError) as excinfo:
        await WalletClient(wallet_client.WALLET_PROXY_BASE_URL).request("/summary/metrics/2061045")
    assert "check WALLET_ID" in excinfo.value.message


@pytest.mark.parametrize("env_overrides,needle", [
    ({"WALLET_ID": "ABC?raw=1#frag"}, "WALLET_ID"),
    ({"WALLET_CACHE_TTL_SECONDS": "soon"}, "WALLET_CACHE_TTL_SECONDS"),
    ({"WALLET_CACHE_MAX_STALE_SECONDS": "tomorrow"}, "WALLET_CACHE_MAX_STALE_SECONDS"),
    ({"WALLET_CACHE_TTL_SECONDS": "-5"}, "WALLET_CACHE_TTL_SECONDS"),
])
def test_invalid_env_config_fails_with_actionable_message_no_traceback(env_overrides, needle):
    """Misconfigured env must fail startup with a clear, actionable message —
    not a raw import-time traceback (mirrors the memory degraded-mode
    philosophy)."""
    result = subprocess.run(
        [sys.executable, "-c", "import wallet_client"],
        env={**os.environ, **env_overrides}, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert needle in result.stderr
    assert "Traceback" not in result.stderr


def test_to_payload_shape():
    err = SourceError("unexpected_format", "bad body")
    assert err.to_payload() == {"error": {"code": "unexpected_format", "message": "bad body"}}


@pytest.mark.parametrize("ticker", ["ABC?raw=1#frag", "../other/endpoint", "ABC\nD", None, 123])
async def test_quote_rejects_unsafe_ticker_without_request(ticker):
    with respx.mock:
        with pytest.raises(SourceError) as excinfo:
            await make_client().get_quote(ticker)
    assert excinfo.value.code == "invalid_params"


@respx.mock
async def test_quote_rejects_missing_required_field():
    respx.get(f"{BASE}/assets/tickers/PETR4").respond(json={"wrong": 1})
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_quote("PETR4")
    assert excinfo.value.code == "unexpected_format"


@respx.mock
async def test_empty_quote_payload_maps_to_ticker_not_found():
    respx.get(f"{BASE}/assets/tickers/VALE99").respond(json={})
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_quote("VALE99")
    assert excinfo.value.code == "ticker_not_found"


@pytest.mark.parametrize("payload", [[1, 2, 3], None, "PETR4", 42])
@respx.mock
async def test_nonempty_wrong_shape_quote_payload_maps_to_unexpected_format(payload):
    """Only a genuinely empty payload means ticker_not_found; any non-empty
    wrong shape (e.g. a JSON array) is a schema drift, not a missing ticker."""
    respx.get(f"{BASE}/assets/tickers/PETR4").respond(json=payload)
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_quote("PETR4")
    assert excinfo.value.code == "unexpected_format"


@pytest.mark.parametrize("value", ["n/a", "NaN", "Infinity", None, True])
@respx.mock
async def test_quote_rejects_unparseable_price(value):
    respx.get(f"{BASE}/assets/tickers/PETR4").respond(json={"variation_day": {"last_quotation": value}})
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_quote("PETR4")
    assert excinfo.value.code == "unexpected_format"


@pytest.mark.parametrize("months", [True, None, "12"])
async def test_history_rejects_noninteger_months(months):
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_patrimony_history(months)
    assert excinfo.value.code == "invalid_params"


async def test_earnings_rejects_single_date_and_bad_type():
    for start, end in [("2026-01-01", None), (None, "2026-01-01"), (12, "2026-02-01")]:
        with pytest.raises(SourceError) as excinfo:
            await make_client().get_earnings(start, end)
        assert excinfo.value.code == "invalid_params"


async def test_earnings_rejects_compact_dates():
    with pytest.raises(SourceError) as excinfo:
        await make_client().get_earnings("20261017", "20261018")
    assert excinfo.value.code == "invalid_params"


@respx.mock
async def test_positions_paginates_until_source_total():
    def rows(start, count):
        return [{"ticker": f"T{i}", "quantity": 1} for i in range(start, start + count)]

    respx.get(f"{BASE}/summary/actives/2061045/Ticker", params={"start": "0"}).respond(
        json={"total": 60, "data": rows(0, 50), "weighted": {}, "draw": 0}
    )
    respx.get(f"{BASE}/summary/actives/2061045/Ticker", params={"start": "50"}).respond(
        json={"total": 60, "data": rows(50, 10), "weighted": {}, "draw": 0}
    )
    envelope = await make_client().get_positions("Ticker")
    assert envelope["data"]["total"] == 60
    assert len(envelope["data"]["data"]) == 60


@respx.mock
async def test_positions_dedupe_when_source_ignores_start():
    """A source that ignores `start` must not double-count holdings (SC-002):
    the same 50 rows on both pages yield 50 unique rows, not 100."""
    def rows(count):
        return [{"ticker": f"T{i}", "quantity": 1} for i in range(count)]

    respx.get(f"{BASE}/summary/actives/2061045/Ticker").respond(
        json={"total": 60, "data": rows(50), "weighted": {}, "draw": 0}
    )
    envelope = await make_client().get_positions("Ticker")
    assert len(envelope["data"]["data"]) == 50
    # The merged total never claims more rows than `data` contains.
    assert envelope["data"]["total"] == 50


@respx.mock
async def test_positions_dedupe_overlapping_pages():
    def rows(start, count):
        return [{"ticker": f"T{i}", "quantity": 1} for i in range(start, start + count)]

    # Page 2 overlaps page 1 (T40..T49 repeat) but adds new rows (T50..T89).
    respx.get(f"{BASE}/summary/actives/2061045/Ticker", params={"start": "0"}).respond(
        json={"total": 70, "data": rows(0, 50), "weighted": {}, "draw": 0}
    )
    respx.get(f"{BASE}/summary/actives/2061045/Ticker", params={"start": "50"}).respond(
        json={"total": 70, "data": rows(40, 50), "weighted": {}, "draw": 0}
    )
    envelope = await make_client().get_positions("Ticker")
    assert len(envelope["data"]["data"]) == 90
    assert envelope["data"]["total"] == 90
    # Every ticker appears exactly once — no double-counted holdings.
    tickers = [row["ticker"] for row in envelope["data"]["data"]]
    assert sorted(tickers, key=lambda t: int(t[1:])) == [f"T{i}" for i in range(90)]


@respx.mock
async def test_positions_collects_beyond_old_thousand_row_cap():
    """The fixed max_pages cap is gone: a class with 1050 positions is fully
    collected (progress-guarded until total)."""
    def rows(start, count):
        return [{"ticker": f"T{i}", "quantity": 1} for i in range(start, start + count)]

    route = respx.get(f"{BASE}/summary/actives/2061045/Ticker")

    def responder(request):
        start = int(request.url.params["start"])
        remaining = 1050 - start
        count = min(50, remaining)
        return httpx.Response(200, json={"total": 1050, "data": rows(start, count), "weighted": {}, "draw": 0})

    route.side_effect = responder
    envelope = await make_client().get_positions("Ticker")
    assert len(envelope["data"]["data"]) == 1050
    assert envelope["data"]["total"] == 1050


@respx.mock
async def test_positions_stops_on_short_page_when_total_missing():
    def rows(start, count):
        return [{"ticker": f"T{i}", "quantity": 1} for i in range(start, start + count)]

    respx.get(f"{BASE}/summary/actives/2061045/Ticker", params={"start": "0"}).respond(
        json={"data": rows(0, 50), "weighted": {}, "draw": 0}
    )
    respx.get(f"{BASE}/summary/actives/2061045/Ticker", params={"start": "50"}).respond(
        json={"data": rows(50, 7), "weighted": {}, "draw": 0}
    )
    envelope = await make_client().get_positions("Ticker")
    assert len(envelope["data"]["data"]) == 57
    assert envelope["data"]["total"] == 57


@pytest.mark.parametrize("today,start", [
    (datetime.date(2024, 2, 29), "2023-02-28"),
    (datetime.date(2026, 10, 17), "2025-10-17"),
])
async def test_default_earnings_uses_calendar_year(monkeypatch, today, start):
    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(wallet_client, "datetime", SimpleNamespace(date=FixedDate, datetime=datetime.datetime))
    with respx.mock:
        route = respx.get(f"{BASE}/earnings/total-period/2061045").respond(json={"sum": 0.0})
        await make_client().get_earnings()
    assert route.calls[0].request.url.params["start_date"] == start
    assert route.calls[0].request.url.params["end_date"] == today.isoformat()
