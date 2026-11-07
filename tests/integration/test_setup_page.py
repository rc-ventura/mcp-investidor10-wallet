import http.client
import json
import re
import socket
import sys
import time
import webbrowser
from urllib.parse import urlencode, urlsplit

import httpx
import pytest
import respx
from fastmcp import Client

from investidor10_wallet import server, setup_page, wallet_client, wallet_config
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

PROXY = wallet_client.WALLET_PROXY_BASE_URL
WALLET = "5551234"
OTHER = "5559876"
CREDENTIAL = "Rq4_credential-T6"
RESTRICTED = f"https://investidor10.com.br/wallet/public/{WALLET}?h={CREDENTIAL}"
PUBLIC = f"https://investidor10.com.br/carteira/{WALLET}"
OTHER_PUBLIC = f"https://investidor10.com.br/carteira/{OTHER}"


@pytest.fixture(autouse=True)
def no_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: True)
    monkeypatch.delenv("WALLET_ID", raising=False)
    monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))


@pytest.fixture
def page():
    setup_page.open_setup()
    session = setup_page.current_session()
    assert session is not None
    return session


def _probe(wallet=WALLET, **kwargs):
    return respx.get(f"{PROXY}/summary/metrics/{wallet}").mock(**kwargs)


def _request(session, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", session.port, timeout=10)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read().decode()
    finally:
        conn.close()


def _post(session, fields, token=None, host=None, origin=None, extra_headers=None):
    origin_value = f"http://127.0.0.1:{session.port}" if origin is None else origin
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": host or f"127.0.0.1:{session.port}",
    }
    if origin_value:
        headers["Origin"] = origin_value
    headers.update(extra_headers or {})
    body = urlencode({"token": session.token if token is None else token, **fields})
    return _request(session, "POST", "/", body=body, headers=headers)


def _save(session, link, mask=False, **kwargs):
    fields = {"link": link, "action": "save"}
    if mask:
        fields["mask"] = "on"
    return _post(session, fields, **kwargs)


def _result(body):
    match = re.search(r'data-result="([a-z_]+)"', body)
    return match.group(1) if match else None


def _saved(home):
    path = wallet_config.config_path(home)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write(home, wallet_id=WALLET, share_hash=None, mask_values=False):
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


def _wait_closed(session, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", session.port), timeout=0.2).close()
        except OSError:
            return True
        time.sleep(0.05)
    return False


def test_the_page_listens_only_on_the_loopback_address(page):
    parts = urlsplit(page.url)
    assert parts.hostname == "127.0.0.1"
    assert page.server_address[0] == "127.0.0.1"
    assert "link" not in parts.query
    assert "h=" not in parts.query.replace("t=", "")


def test_the_form_is_served_with_the_token_and_safe_headers(page):
    path = urlsplit(page.url).path + "?" + urlsplit(page.url).query
    status, headers, body = _request(page, "GET", path)

    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    csp = headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "form-action 'self'" in csp
    assert headers["Referrer-Policy"] == "same-origin"
    assert 'type="password"' in body
    assert 'name="mask"' in body
    assert re.search(r"<(script|link|img)[^>]+(src|href)=\"https?://", body) is None


def test_get_without_the_token_is_refused(page):
    status, _, body = _request(page, "GET", "/")
    assert status == 403
    assert 'name="link"' not in body


@respx.mock
def test_a_valid_restricted_link_is_saved_and_the_page_closes(page, isolated_home):
    route = _probe(return_value=httpx.Response(200, json={"applied": 1}))

    status, headers, body = _save(page, RESTRICTED, mask=True)

    assert status == 200
    assert _result(body) == "saved"
    assert headers["Cache-Control"] == "no-store"
    assert route.calls.last.request.url.params["hash"] == CREDENTIAL
    config = _saved(isolated_home)
    assert config["wallet_id"] == WALLET
    assert config["share_hash"] == CREDENTIAL
    assert config["mode"] == "restricted"
    assert config["mask_values"] is True
    assert config["source"] == "setup_page"
    assert "…34" in body
    assert WALLET not in body and CREDENTIAL not in body
    assert page.state == "saved"
    assert _wait_closed(page)


@respx.mock
def test_a_public_link_is_saved_with_the_indexing_warning(page, isolated_home):
    _probe(return_value=httpx.Response(200, json={"applied": 1}))

    _, _, body = _save(page, PUBLIC)

    assert _result(body) == "saved"
    assert "indexada" in body
    assert "restrita" in body
    assert _saved(isolated_home)["mode"] == "public"


@respx.mock
def test_another_wallet_asks_for_confirmation_before_writing(page, isolated_home):
    _write(isolated_home)
    before = wallet_config.config_path(isolated_home).read_bytes()
    _probe(OTHER, return_value=httpx.Response(200, json={"applied": 1}))

    _, _, body = _save(page, OTHER_PUBLIC)

    assert _result(body) == "confirm_switch"
    assert "…34" in body and "…76" in body
    assert "memória" in body
    assert OTHER not in body
    assert wallet_config.config_path(isolated_home).read_bytes() == before
    assert page.state == "open"


@respx.mock
def test_the_confirmed_switch_writes_the_new_wallet(page, isolated_home):
    _write(isolated_home)
    _probe(OTHER, return_value=httpx.Response(200, json={"applied": 1}))
    _save(page, OTHER_PUBLIC)

    _, _, body = _post(page, {"action": "confirm"})

    assert _result(body) == "saved"
    assert _saved(isolated_home)["wallet_id"] == OTHER
    assert _saved(isolated_home)["source"] == "setup_page"


@respx.mock
def test_confirm_without_a_pending_switch_writes_nothing(page, isolated_home):
    _, _, body = _post(page, {"action": "confirm"})
    assert _result(body) == "invalid_link"
    assert _saved(isolated_home) is None


@respx.mock
def test_only_the_mask_or_the_credential_of_the_same_wallet_needs_no_confirmation(
    page, isolated_home
):
    _write(isolated_home)
    _probe(return_value=httpx.Response(200, json={"applied": 1}))

    _, _, body = _save(page, RESTRICTED, mask=True)

    assert _result(body) == "saved"
    config = _saved(isolated_home)
    assert config["share_hash"] == CREDENTIAL
    assert config["mask_values"] is True


@respx.mock
def test_the_same_values_change_nothing(page, isolated_home):
    _write(isolated_home)
    path = wallet_config.config_path(isolated_home)
    before = (path.stat().st_mtime_ns, path.read_bytes())
    _probe(return_value=httpx.Response(200, json={"applied": 1}))

    _, _, body = _save(page, PUBLIC)

    assert _result(body) == "unchanged"
    assert (path.stat().st_mtime_ns, path.read_bytes()) == before


@pytest.mark.parametrize(
    "text", ["", "https://example.com/carteira/1", "não sei", "12a34"]
)
def test_an_unreadable_link_lists_the_valid_forms(page, isolated_home, text):
    _, _, body = _save(page, text)
    assert _result(body) == "invalid_link"
    assert "investidor10.com.br/carteira/" in body
    assert _saved(isolated_home) is None


@pytest.mark.parametrize("status", [301, 401, 403])
@respx.mock
def test_access_denied_explains_the_cause_and_writes_nothing(
    page, isolated_home, status
):
    _probe(return_value=httpx.Response(status))

    _, _, body = _save(page, RESTRICTED)

    assert _result(body) == "access_denied"
    assert "privada" in body and "restrita" in body
    assert _saved(isolated_home) is None
    assert CREDENTIAL not in body


@respx.mock
def test_a_missing_wallet_writes_nothing(page, isolated_home):
    _probe(return_value=httpx.Response(404))
    _, _, body = _save(page, PUBLIC)
    assert _result(body) == "not_found"
    assert _saved(isolated_home) is None


@pytest.mark.parametrize(
    "mock",
    [
        {"return_value": httpx.Response(503)},
        {"side_effect": httpx.ConnectTimeout("timed out")},
    ],
)
@respx.mock
def test_an_unavailable_source_writes_nothing(page, isolated_home, mock):
    _probe(**mock)
    _, _, body = _save(page, PUBLIC)
    assert _result(body) == "unavailable"
    assert _saved(isolated_home) is None
    assert page.state == "open"


@respx.mock
def test_a_failed_write_points_to_the_terminal(page, isolated_home, monkeypatch):
    _probe(return_value=httpx.Response(200, json={"applied": 1}))

    def refuse(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(wallet_config, "write_config", refuse)

    _, _, body = _save(page, PUBLIC)

    assert _result(body) == "save_failed"
    assert "mcp-investidor10-wallet configure" in body
    assert page.state == "open"


@respx.mock
def test_a_configuration_from_a_future_version_is_left_untouched(page, isolated_home):
    path = wallet_config.config_path(isolated_home)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    path.write_text(json.dumps({"version": 9}), encoding="utf-8")
    _probe(return_value=httpx.Response(200, json={"applied": 1}))

    _, _, body = _save(page, PUBLIC)

    assert _result(body) == "future_version"
    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 9}


@pytest.mark.parametrize(
    "variant",
    [
        {"token": ""},
        {"token": "forged-token"},
        {"host": "evil.example:80"},
        {"host": "localhost:1"},
        {"origin": "https://evil.example"},
        {"origin": "null"},
        {"origin": ""},
    ],
    ids=[
        "no_token",
        "wrong_token",
        "wrong_host",
        "other_port",
        "other_origin",
        "null",
        "missing_origin",
    ],
)
@respx.mock
def test_forged_submissions_are_refused_without_writing(page, isolated_home, variant):
    route = _probe(return_value=httpx.Response(200, json={"applied": 1}))
    if "host" in variant:
        variant = {"host": variant["host"].replace(":1", f":{page.port + 1}")}

    status, _, _ = _save(page, PUBLIC, **variant)

    assert status == 403
    assert _saved(isolated_home) is None
    assert route.call_count == 0
    assert page.state == "open"


@respx.mock
def test_a_used_token_is_refused(page, isolated_home):
    _probe(return_value=httpx.Response(200, json={"applied": 1}))
    _probe(OTHER, return_value=httpx.Response(200, json={"applied": 1}))
    assert _result(_save(page, PUBLIC)[2]) == "saved"
    _wait_closed(page)
    before = _saved(isolated_home)

    with pytest.raises(OSError):
        _save(page, OTHER_PUBLIC)

    assert page.check_token(page.token) is False
    assert _saved(isolated_home) == before


@respx.mock
def test_an_expired_token_is_refused_and_the_page_closes(
    page, isolated_home, monkeypatch
):
    route = _probe(return_value=httpx.Response(200, json={"applied": 1}))
    now = setup_page.clock()
    monkeypatch.setattr(
        setup_page, "clock", lambda: now + setup_page.TOKEN_TTL_SECONDS + 1
    )

    status, _, _ = _save(page, PUBLIC)

    assert status == 410
    assert _saved(isolated_home) is None
    assert route.call_count == 0
    assert page.state == "expired"
    assert _wait_closed(page)


def test_the_token_lasts_ten_minutes():
    assert setup_page.TOKEN_TTL_SECONDS == 600


@respx.mock
def test_an_expired_page_is_replaced_by_a_new_one(page, monkeypatch):
    now = setup_page.clock()
    monkeypatch.setattr(
        setup_page, "clock", lambda: now + setup_page.TOKEN_TTL_SECONDS + 1
    )

    result = setup_page.open_setup()

    assert result["status"] == "opened"
    assert setup_page.current_session() is not page
    assert setup_page.current_session().token != page.token


def test_an_oversized_body_is_refused(page, isolated_home):
    status, _, _ = _post(page, {"link": "x" * 70000, "action": "save"})
    assert status == 413
    assert _saved(isolated_home) is None


@respx.mock
def test_no_response_repeats_the_link_or_the_credential(page, isolated_home):
    _probe(return_value=httpx.Response(301))
    bodies = [_save(page, RESTRICTED)[2], _save(page, f"veja {RESTRICTED} e")[2]]
    _probe(return_value=httpx.Response(503))
    bodies.append(_save(page, RESTRICTED)[2])
    for body in bodies:
        assert CREDENTIAL not in body
        assert WALLET not in body
        assert RESTRICTED not in body


@respx.mock
def test_the_submitted_body_never_reaches_logs(page, isolated_home, capfd):
    _probe(return_value=httpx.Response(200, json={"applied": 1}))

    _save(page, RESTRICTED)

    out, err = capfd.readouterr()
    for text in (out, err):
        assert CREDENTIAL not in text
        assert WALLET not in text
        assert page.token not in text


@respx.mock
async def test_the_saved_configuration_applies_to_the_next_tool_call(
    page, isolated_home
):
    async with Client(mcp) as client:
        pending = await client.call_tool("get_wallet_summary", {}, raise_on_error=False)
    assert pending.structured_content["error"]["code"] == "wallet_not_configured"
    _probe(return_value=httpx.Response(200, json={"applied": 1, "equity": 2}))

    _, _, body = _save(page, RESTRICTED)
    assert _result(body) == "saved"

    async with Client(mcp) as client:
        result = await client.call_tool("get_wallet_summary", {}, raise_on_error=False)
        context = await client.call_tool("get_session_context", {})
    assert result.is_error is False
    assert result.structured_content["data"]["equity"] == 2
    assert context.structured_content["configuration"]["mode"] == "restricted"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
@respx.mock
def test_the_saved_file_is_private(page, isolated_home):
    _probe(return_value=httpx.Response(200, json={"applied": 1}))
    _save(page, PUBLIC)
    path = wallet_config.config_path(isolated_home)
    assert path.stat().st_mode & 0o777 == 0o600
