"""MCP server: Investidor10 wallet agent with long-term investor memory.

Runs over stdio (the agent client spawns this process; no network exposed).
Tool registration happens per user story; this module owns the app instance,
the shared memory store, and the structured error helpers used by all tools.

Specs: specs/001-mcp-investidor10-wallet/ (plan.md, contracts/mcp-tools.md)
"""

import os

import wallet_client
from fastmcp import FastMCP
from memory_store import MemoryStore, MemoryUnavailableError

mcp = FastMCP("investidor10-wallet")

memory = MemoryStore(os.getenv("WALLET_MEMORY_PATH", "memory.json"))


def source_error_payload(exc: wallet_client.SourceError) -> dict:
    """Convert a data-source failure into the structured error envelope."""
    return exc.to_payload()


def memory_error_payload(exc: MemoryUnavailableError) -> dict:
    """Convert a memory-store failure into the structured error envelope.

    The agent should inform the user and keep operating without memory
    (spec edge case: corrupted memory must not disable the other tools).
    """
    return {"error": {"code": "memory_unavailable", "message": str(exc)}}


if __name__ == "__main__":
    mcp.run()
