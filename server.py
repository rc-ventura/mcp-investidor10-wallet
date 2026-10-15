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


# --------------------------------------------------------------------- wallet tools


@mcp.tool
async def get_wallet_summary() -> dict:
    """Overview of the configured wallet: applied amount, patrimony (equity),
    variation, and total and 12-month returns.

    Use this first when the user asks "how is my wallet doing?". The response is
    a data envelope: always tell the user the data freshness by mentioning
    `fetched_at` and whether the answer came from the in-memory cache
    (`cached=true`). On failure this returns {"error": {"code", "message"}} —
    never invent values.
    """
    try:
        return await wallet_client.wallet_client.get_summary()
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_wallet_allocation() -> dict:
    """Wallet allocation broken down by asset (ticker) and by asset class.

    Use together with get_wallet_positions to compare the current allocation
    against the ideal one. This is also a data envelope — always mention
    `fetched_at` and `cached` when presenting the numbers.
    """
    try:
        return await wallet_client.wallet_client.get_allocation()
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_wallet_positions(asset_type: str) -> dict:
    """Detailed positions of one asset class of the wallet.

    Args:
        asset_type: One of Ticker (Brazilian stocks), Fii (real estate funds),
            EtfInternational (international ETFs), Treasure (Brazilian treasury
            bonds), Crypto. Any case is accepted; other values return an
            invalid_asset_type error listing the valid types.

    Each position includes quantity, average price, current quote, equity,
    profitability, percent of wallet (percent_wallet), ideal percent
    (percent_ideal), fundamental indicators when the class provides them
    (P/E, P/B, dividend yield, ROE) and the source's buy flag. A class with no
    positions returns data as an empty list (not an error). Never invent
    indicator values that the source did not provide.

    Presentation rules: compare percent_wallet vs percent_ideal when discussing
    rebalancing; for EtfInternational positions, remind the user that equity
    involves currency conversion; always mention `cached` and `fetched_at`.
    """
    try:
        return await wallet_client.wallet_client.get_positions(asset_type)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


if __name__ == "__main__":
    mcp.run()
