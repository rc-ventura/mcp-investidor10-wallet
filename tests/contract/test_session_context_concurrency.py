import errno

import filelock
import pytest
from fastmcp import Client

from investidor10_wallet import server
from investidor10_wallet.memory_store import (
    MemoryBusyError,
    MemoryReadOnlyError,
    MemoryStore,
)
from investidor10_wallet.server import mcp


def test_memory_error_payload_uses_the_exception_code():
    assert server.memory_error_payload(MemoryBusyError("x"))["error"]["code"] == (
        "memory_busy"
    )
    assert server.memory_error_payload(MemoryReadOnlyError("x"))["error"]["code"] == (
        "memory_read_only"
    )


async def test_session_context_reports_read_only_and_does_not_write(
    tmp_path, monkeypatch
):
    path = str(tmp_path / "memory.json")
    MemoryStore(path).save_rule("kept")

    def refuse(self, *args, **kwargs):
        raise OSError(errno.ENOSYS, "Function not implemented")

    monkeypatch.setattr(filelock.FileLock, "acquire", refuse)
    store = MemoryStore(path)
    monkeypatch.setattr(server, "memory", store)

    async with Client(mcp) as client:
        result = await client.call_tool("get_session_context", {}, raise_on_error=False)

    payload = result.structured_content
    assert payload["memory_status"] == "read_only"
    assert payload["triggered_alerts"] == []
    assert [r["text"] for r in payload["memory"]["rules"]] == ["kept"]


async def test_session_context_returns_memory_busy_instead_of_unavailable(
    tmp_path, monkeypatch
):
    path = str(tmp_path / "memory.json")
    store = MemoryStore(path, lock_timeout=0.2)
    monkeypatch.setattr(server, "memory", store)

    with filelock.FileLock(f"{path}.lock"):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_session_context", {}, raise_on_error=False
            )

    assert result.structured_content["error"]["code"] == "memory_busy"


@pytest.mark.parametrize("tool", ["save_rule", "log_insight"])
async def test_write_tools_report_memory_busy(tmp_path, monkeypatch, tool):
    path = str(tmp_path / "memory.json")
    monkeypatch.setattr(server, "memory", MemoryStore(path, lock_timeout=0.2))
    arguments = (
        {"text": "r"}
        if tool == "save_rule"
        else {"kind": "k", "fingerprint": "f", "summary": "s"}
    )

    with filelock.FileLock(f"{path}.lock"):
        async with Client(mcp) as client:
            result = await client.call_tool(tool, arguments, raise_on_error=False)

    assert result.structured_content["error"]["code"] == "memory_busy"
