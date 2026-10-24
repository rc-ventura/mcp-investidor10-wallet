# CLAUDE.md

## ADRs — Technical Decisions

> Folder: `./docs/adrs/`

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](./docs/adrs/0001-platform-and-storage-choices.md) | Platform and storage choices — FastMCP, httpx + TTL cache, single JSON store, pinned deps | Accepted | 2026-10-17 |
| [0002](./docs/adrs/0002-memory-persistence-and-alert-delivery.md) | Memory persistence boundary and alert delivery semantics | Accepted | 2026-10-17 |
| [0003](./docs/adrs/0003-stale-cache-age-and-pagination-merge.md) | Stale-cache age policy and boundary-semantics unification | Accepted | 2026-10-17 |
| [0004](./docs/adrs/0004-threat-model-and-security-boundary.md) | Threat model and security boundary of the single-user stdio server | Accepted | 2026-10-17 |
| [0005](./docs/adrs/0005-undocumented-internal-api-dependency.md) | Dependence on Investidor10's undocumented internal API | Accepted | 2026-10-17 |
| [0006](./docs/adrs/0006-embedded-memory-and-deterministic-bootstrap.md) | Embedded domain memory with a deterministic session bootstrap | Accepted | 2026-10-17 |
| [0007](./docs/adrs/0007-passthrough-envelope-and-structured-errors.md) | Source passthrough with data envelope and structured errors | Accepted | 2026-10-17 |
| [0008](./docs/adrs/0008-stateless-mcp-protocol-and-explicit-state.md) | Stateless MCP protocol (revision 2026-07-28) — explicit state alignment | Accepted | 2026-10-17 |
| [0009](./docs/adrs/0009-idioma-das-mensagens-operador-vs-modelo.md) | Idioma das mensagens: operador em PT-BR, modelo em inglês | Accepted | 2026-10-18 |
| [0010](./docs/adrs/0010-ciclo-de-vida-do-bootstrap-e-migracao.md) | Semântica do ciclo de vida do bootstrap e endurecimento da migração | Accepted | 2026-10-18 |
| [0011](./docs/adrs/0011-estrategia-de-distribuicao-e-release.md) | Estratégia de distribuição e release — PyPI via `uvx`, src layout, versionamento 0.x e pipeline OIDC | Accepted | 2026-10-18 |

## Learning Lessons

> Folder: `./docs/learning-lessons/`

- [get_asset_quote só cobre ações da B3 — FIIs, ETFs internacionais, cripto e tesouro retornam HTTP 410](./docs/learning-lessons/get_asset_quote_apenas_acoes_b3.md) — 2026-10-15
- [API upstream tem detalhe de proventos por ativo — o MCP só expõe o total agregado](./docs/learning-lessons/earnings_list_detalhe_proventos_por_ativo.md) — 2026-10-17
- [Efeito bola de neve: usar rendimento recorrente atual, nunca DY médio](./docs/learning-lessons/efeito_bola_de_neve_calculo.md) — 2026-10-17
- [Endpoints paginados podem ignorar `start`: proteja o merge com dedupe e guarda de progresso](./docs/learning-lessons/paginacao_merge_guardar_dedupe_e_progresso.md) — 2026-10-17