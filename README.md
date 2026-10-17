# mcp-investidor10-wallet

MCP server that connects an agent client (Claude Desktop, Claude Code, Devin) to a
public [Investidor10](https://investidor10.com.br) wallet, with a built-in long-term
investor memory (theses, rules, decisions, communicated-insight log) and price alerts.

No frontend — the agent client is the interface. The server runs over stdio
(the client spawns the process; no network is exposed).

## Status

All 19 tools implemented (6 wallet/market data + 13 memory/alerts) — see
[`specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md`](specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md)
for the full contracts and
[`specs/001-mcp-investidor10-wallet/tasks.md`](specs/001-mcp-investidor10-wallet/tasks.md)
for the task history.

## Install & run

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                # install pinned dependencies
WALLET_ID=1234567 uv run server.py     # run the MCP server over stdio
```

## Client configuration

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "carteira": {
      "command": "uv",
      "args": ["--directory", "/Users/rafaelventura/CascadeProjects/mcp-investidor10-wallet", "run", "server.py"],
      "env": { "WALLET_ID": "1234567" }
    }
  }
}
```

**Claude Code**:

```bash
claude mcp add carteira -- uv --directory ~/CascadeProjects/mcp-investidor10-wallet run server.py
```

**Devin CLI** (local scope, gitignored):

```bash
devin mcp add carteira -- uv --directory /Users/rafaelventura/CascadeProjects/mcp-investidor10-wallet run server.py
```

The server is respawned by the client whenever a session starts or a tool is
called; restart the client session to pick up new tools after an upgrade.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `WALLET_ID` | `1234567` | Public wallet ID on Investidor10 (FR-013) |
| `WALLET_MEMORY_PATH` | `memory.json` | Path of the long-term memory store |
| `WALLET_CACHE_TTL_SECONDS` | `600` | TTL for caching API responses (FR-014) |

## Tools (19)

- **Wallet/market data (6)**: `get_wallet_summary`, `get_wallet_allocation`,
  `get_wallet_positions`, `get_patrimony_history`, `get_earnings`, `get_asset_quote`
- **Memory & alerts (13)**: `get_session_context` (session bootstrap — call it at
  the start of every session), `get_wallet_goal`, `set_wallet_goal`, `save_thesis`,
  `get_theses`, `save_rule`, `get_rules`, `log_decision`, `record_decision_outcome`,
  `log_insight`, `create_price_alert`, `list_price_alerts`, `cancel_price_alert`

## Tests

```bash
uv run pytest          # unit + contract tests (API mocked with respx)
uv run pytest -m live  # opt-in integration tests against the real API
```

## Data flow

- Wallet/market data comes from Investidor10's public (no-auth) API and is returned
  as `{"cached": bool, "fetched_at": ISO-8601, "data": ...}` so the agent always
  tells the user how fresh the data is. B3 quotes have an inherent ~15 min delay.
- Long-term memory is a local versioned JSON file with atomic writes. A corrupted
  file degrades the store into an explicit "memory unavailable" mode — the data
  tools keep working and nothing is silently lost.
- Price alerts are evaluated only at session open (`get_session_context`), never
  continuously; a triggered alert is terminal and never fires twice.

## Limitations & risks

- **Undocumented internal API**: the Investidor10 endpoints are public but
  undocumented and may change or require auth without notice. Failures surface
  as explicit structured errors, never fabricated values (FR-016).
- **Quote coverage**: `get_asset_quote` only covers B3 stocks; FIIs,
  international ETFs, crypto and treasury return `asset_type_not_supported`
  (see [learning lesson](docs/learning-lessons/get_asset_quote_apenas_acoes_b3.md)).
  Wallet-held assets of those classes still appear via `get_wallet_positions`.
- **Earnings detail**: `get_earnings` returns the period aggregate; the per-asset
  payment table exists upstream (`/earnings/list/{id}`) and is a candidate for a
  future `get_earnings_detailed` tool (see
  [learning lesson](docs/learning-lessons/earnings_list_detalhe_proventos_por_ativo.md)).
- **Quotes are delayed** (~15 min on B3); the agent must always state this.
- **Personal/educational use**: the agent suggests, never executes orders.
- See [`CLAUDE.md`](CLAUDE.md) for the learning-lesson index.