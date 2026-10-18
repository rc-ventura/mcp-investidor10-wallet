# Implementation Plan: Agente de Investimentos conectado à Carteira Investidor10

**Branch**: `001-mcp-investidor10-wallet` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-mcp-investidor10-wallet/spec.md`

## Summary

Servidor MCP em Python (FastMCP, transport stdio) que conecta clientes de agente (Claude Desktop/Code, Devin) à API interna pública do Investidor10 Wallet. Expõe 6 tools de dados da carteira/mercado (resumo, alocação, posições, evolução patrimonial, proventos, cotações) e um subsistema de memória de longo prazo **embutido no próprio servidor** (teses, regras, decisões com desfecho, log de insights, alertas de preço com estado), persistido em `memory.json` local versionado com escrita atômica. Uma tool determinística `get_session_context` é chamada pelo agente no início de cada sessão para carregar o contexto do investidor e verificar alertas ativos contra cotações atuais, marcando os disparados (sem repetição). Cache em memória com TTL configurável (~10 min) protege a fonte de dados. Sem frontend; insights (rebalanceamento, aporte, renda passiva, relatórios com web) são gerados pelo modelo do cliente a partir dos dados das tools.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `fastmcp` (pin `4.0.10`, publicada há ≥7 dias), `httpx` (pin `0.28.1`). Dev: `pytest`, `pytest-asyncio`, `respx` (mock de httpx).

**Storage**: `memory.json` local (schema versionado, escrita atômica tmp+rename) — path configurável via `WALLET_MEMORY_PATH`. Cache de API apenas em memória de processo (TTL via `WALLET_CACHE_TTL_SECONDS`, padrão 600s).

**Testing**: pytest com respx para mockar a API Investidor10; testes de unidade do memory store (incl. corrupção/fallback); testes de integração contra a API real marcados como `live` (opt-in).

**Target Platform**: macOS (local, processo spawned pelo cliente MCP via stdio); portável para Linux.

**Project Type**: MCP server (serviço stdio, sem rede exposta, sem frontend).

**Performance Goals**: tool com cache hit < 100ms; tool com chamada à API < 5s; visão completa da carteira (múltiplas tools compostas pelo agente) < 30s (SC-001).

**Constraints**: carteira pública sem auth (apenas `wallet_id` + User-Agent de browser); um usuário/uma carteira ativa; código, docstrings e mensagens de erro em inglês (decisão do usuário, 2026-10-10 — interação com o usuário permanece pt-BR); falhas da fonte sempre explícitas, nunca valores fabricados (FR-016); nenhuma execução de ordens.

**Scale/Scope**: 1 usuário, ~22 ativos em 5 classes, 19 tools MCP, store de memória na ordem de centenas de entradas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` está como template não preenchido (sem princípios definidos) — **nenhum gate aplicável**. Nenhuma violação a justificar.

*Re-check pós-Phase 1*: o design usa um único processo, duas dependências de runtime e um arquivo JSON — sem complexidade adicional que exigiria justificativa. Sem mudanças.

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-investidor10-wallet/
├── plan.md              # Este arquivo
├── research.md          # Phase 0 — decisões (FastMCP, memória embutida, storage JSON, alertas)
├── data-model.md        # Phase 1 — entidades, schema do memory.json, máquina de estados de alertas
├── quickstart.md        # Phase 1 — setup e cenários de validação ponta a ponta
├── contracts/
│   └── mcp-tools.md     # Phase 1 — contrato das 19 tools MCP (args, retorno, erros)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado por este comando)
```

### Source Code (repository root)

```text
mcp-investidor10-wallet/
├── pyproject.toml          # deps: fastmcp, httpx (pin); dev: pytest, pytest-asyncio, respx
├── README.md
├── server.py               # FastMCP app + registro das tools (fachada fina)
├── wallet_client.py        # cliente httpx async + cache TTL + normalização de erros da API
├── memory_store.py         # store JSON versionado: load/save atômico, CRUD de teses/regras/decisões/insights/alertas
├── memory.json             # criado em runtime (gitignored); path via WALLET_MEMORY_PATH
└── tests/
    ├── unit/
    │   ├── test_memory_store.py   # CRUD, corrupção → modo sem memória, escrita atômica
    │   ├── test_wallet_client.py  # cache TTL, erros, parsing (respx mock)
    │   └── test_alerts.py         # avaliação de condições, transição active→triggered, sem duplicidade
    ├── contract/
    │   └── test_tools_schemas.py  # shapes de retorno conforme contracts/mcp-tools.md
    └── integration/
        └── test_live_api.py       # marcado `live`, opt-in contra API real
```

**Structure Decision**: projeto único, layout flat (sem `src/` package) — o servidor é um único processo com três módulos coesos; empacotamento prematuro não agrega. `memory_store.py` isola o storage para migração futura (JSON → SQLite) sem tocar nas tools.

## Complexity Tracking

Nenhuma violação de constitution a justificar (constitution vazia; design minimalista).
