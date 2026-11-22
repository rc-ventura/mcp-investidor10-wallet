import asyncio
import http.client
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import respx
from fastmcp import Client

from investidor10_wallet import server, wallet_config
from investidor10_wallet.memory_store import MemoryStore
from investidor10_wallet.server import mcp

ROOT = Path(__file__).resolve().parents[2]
WORKER = Path(__file__).resolve().parent / "setup_worker.py"
PROXY = "https://investidor10.com.br/wallet/api/proxy/wallet-app"
FIRST = "3330001"
SECOND = "3330002"


def _post(url, fields):
    parts = urlsplit(url)
    token = dict(pair.split("=", 1) for pair in parts.query.split("&"))["t"]
    conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
    try:
        conn.request(
            "POST",
            "/",
            body=urlencode({"token": token, **fields}),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": f"http://{parts.hostname}:{parts.port}",
            },
        )
        return conn.getresponse().read().decode()
    finally:
        conn.close()


async def _summary_and_context():
    async with Client(mcp) as client:
        summary = await client.call_tool("get_wallet_summary", {})
        context = await client.call_tool("get_session_context", {})
    return summary, context


@respx.mock
def test_a_page_saved_by_another_process_is_used_without_restart(
    isolated_home, tmp_path, monkeypatch
):
    monkeypatch.delenv("WALLET_ID", raising=False)
    monkeypatch.setattr(server, "memory", MemoryStore(str(tmp_path / "memory.json")))
    wallet_config.write_config(
        isolated_home,
        wallet_config.LocalConfig(
            wallet_id=FIRST,
            share_hash=None,
            mode="public",
            mask_values=False,
            validated_at="2026-11-06T10:00:00-03:00",
            source="configure",
        ),
    )
    first = respx.get(f"{PROXY}/summary/metrics/{FIRST}").respond(
        json={"applied": 1, "equity": 1}
    )
    second = respx.get(f"{PROXY}/summary/metrics/{SECOND}").respond(
        json={"applied": 2, "equity": 2}
    )
    before, _ = asyncio.run(_summary_and_context())
    assert before.structured_content["data"]["equity"] == 1

    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(WORKER.parent)]),
        "HTTPS_PROXY": "http://127.0.0.1:1",
    }
    worker = subprocess.Popen(
        [sys.executable, str(WORKER)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        url = json.loads(worker.stdout.readline())["setup_url"]
        link = f"https://investidor10.com.br/carteira/{SECOND}"
        assert 'data-result="confirm_switch"' in _post(
            url, {"link": link, "action": "save"}
        )
        assert 'data-result="saved"' in _post(url, {"action": "confirm"})
        assert worker.wait(timeout=30) == 0, worker.stderr.read()
    finally:
        if worker.poll() is None:
            worker.kill()

    after, context = asyncio.run(_summary_and_context())

    assert after.structured_content["data"]["equity"] == 2
    assert first.call_count == 1
    assert second.call_count == 1
    assert context.structured_content["configuration"]["wallet"] == "…02"
