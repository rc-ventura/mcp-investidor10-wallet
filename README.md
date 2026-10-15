# mcp-investidor10-wallet

MCP server that connects an agent client (Claude Desktop, Claude Code, Devin) to a
public [Investidor10](https://investidor10.com.br) wallet, with a built-in long-term
investor memory (theses, rules, decisions, communicated-insight log) and price alerts.

No frontend — the agent client is the interface. The server runs over stdio.

## Status

Stage 1 (foundation): HTTP client with TTL cache, memory store (schema v1, atomic
writes, degraded mode), server skeleton. Tools are registered in the next stages —
see `specs/001-mcp-investidor10-wallet/tasks.md`.

## Install & run

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                # install pinned dependencies
WALLET_ID=1234567 uv run server.py     # run the MCP server over stdio
```

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `WALLET_ID` | `1234567` | Public wallet ID on Investidor10 (FR-013) |
| `WALLET_MEMORY_PATH` | `memory.json` | Path of the long-term memory store |
| `WALLET_CACHE_TTL_SECONDS` | `600` | TTL for caching API responses (FR-014) |

## Tests

```bash
uv run pytest          # unit + contract tests (API mocked with respx)
uv run pytest -m live  # opt-in integration tests against the real API
```

## Tools (19 planned)

The full tool contracts — 6 wallet/market data tools and 13 memory/alert tools — are
specified in [`specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md`](specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md).

## Data flow

- Wallet/market data comes from Investidor10's public (no-auth) API and is returned
  as `{"cached": bool, "fetched_at": ISO-8601, "data": ...}` so the agent always
  tells the user how fresh the data is. B3 quotes have an inherent ~15 min delay.
- Long-term memory is a local versioned JSON file with atomic writes. A corrupted
  file degrades the store into an explicit "memory unavailable" mode — the data
  tools keep working and nothing is silently lost.
