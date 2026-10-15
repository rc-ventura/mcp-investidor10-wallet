# Quickstart — Validação do Agente Investidor10 Wallet

Guia de validação ponta a ponta. Detalhes de contratos em [contracts/mcp-tools.md](contracts/mcp-tools.md) e modelo de dados em [data-model.md](data-model.md).

## Pré-requisitos

- Python 3.11+ e [`uv`](https://docs.astral.sh/uv/) instalados
- Carteira pública no Investidor10 (ID default `1234567`, configurável via env)
- Um cliente MCP: Claude Desktop, Claude Code ou Devin CLI

## Setup

```bash
cd ~/CascadeProjects/mcp-investidor10-wallet
uv sync                    # instala fastmcp + httpx (pinados)

# Smoke test sem cliente MCP:
WALLET_ID=1234567 uv run server.py   # sobe em stdio; Ctrl+C para sair
```

Testes:

```bash
uv run pytest                  # unit + contract (tudo mockado com respx)
uv run pytest -m live          # opt-in: integração contra a API real do Investidor10
```

## Configuração nos clientes

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

**Claude Code**: `claude mcp add carteira -- uv --directory ~/CascadeProjects/mcp-investidor10-wallet run server.py`

**Devin CLI**: adicionar o mesmo comando ao `~/.config/devin/mcp.json` (ver docs do `devin-cli` skill para o formato exato).

## Cenários de validação (por user story)

### Story 1 — Visão completa da carteira (P1)
1. No cliente, pergunte: **"como está minha carteira?"**
2. Esperado: patrimônio, aplicado, rentabilidade total e 12M, alocação por classe e as posições das 5 classes (ações, FIIs, ETFs int., Tesouro, cripto) com PM, cotação e indicadores.
3. Conferência: números idênticos à página pública da carteira (SC-001, SC-002). Pergunte duas vezes seguidas — a segunda deve indicar dados de cache (FR-014).

### Story 2 — Rebalanceamento e aporte (P2)
1. Pergunte: **"quais ativos estão acima do peso ideal?"**
2. Esperado: lista de desvios `% atual vs % ideal` ordenados por magnitude (ex.: PETR4 15,2% vs 8%), precisão de 0,1 p.p. (SC-003).
3. Pergunte: **"tenho R$ 2.000 pra aportar, onde coloco?"** — esperado: distribuição priorizando ativos abaixo do ideal com flag `buy` positiva; nenhuma sugestão de venda não solicitada.

### Story 3 — Memória de longo prazo (P2)
1. Diga: **"minha tese pra PETR4 é payout alto com capex contido. Minha regra: só compro com recomendação positiva. Meu objetivo é aposentadoria."**
2. **Feche o cliente e abra nova sessão.** Pergunte: "o que você sabe sobre minha estratégia?" e "qual minha tese pra PETR4?"
3. Esperado: agente recupera tudo com datas (SC-004) — prova de que `get_session_context` foi chamado no bootstrap.
4. Peça análise de rebalanceamento; recuse uma sugestão com justificativa. Na sessão seguinte, o agente não deve repeti-la sem novo fundamento (FR-010).

### Story 4 — Cotações (P2)
1. Pergunte: **"cotação e indicadores de VALE3 hoje"**.
2. Esperado: preço, variações, Graham/Bazin, P/L, P/VP, DY, setor, com aviso explícito da defasagem (~15 min, SC-007). Ticker inválido (`VALE99`) → erro claro de não encontrado.

### Story 5 — Renda passiva e patrimônio (P3)
1. **"Quanto recebi de proventos nos últimos 12 meses?"** — total confere com a fonte (SC-002).
2. **"Como meu patrimônio evoluiu em 24 meses?"** — série mensal separando aporte de valorização.
3. Período invertido ("de out/2026 a jan/2026") → agente questiona/corrige, nunca vazio silencioso.

### Story 6 — Alertas de preço (P3)
1. Peça: **"me avise quando PETR4 cair abaixo de R$ 999"** (condição já satisfeita).
2. **Abra nova sessão.** Esperado: o alerta é entregue no início, com preço atual e data de registro; marcado como disparado (SC-006).
3. Abra outra sessão — o alerta NÃO reaparece. `list_price_alerts` mostra `state=triggered`.

### Falhas esperadas (edge cases)
- Renomeie/corrompa `memory.json` e inicie sessão → agente avisa do modo sem memória e as tools de dados continuam funcionando; arquivo original preservado como `.broken-<timestamp>`.
- Derrube a rede e peça o resumo → erro explícito de indisponibilidade; se houver cache recente, é apresentado com a idade dos dados declarada.
