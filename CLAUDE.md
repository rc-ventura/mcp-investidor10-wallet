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
| [0012](./docs/adrs/0012-integracao-automatica-de-clientes.md) | Integração automática de clientes — assistente de instalação e plugin de comportamento (bundle em 4 CLIs) | Accepted | 2026-10-26 |
| [0013](./docs/adrs/0013-concorrencia-da-memoria-multiprocesso.md) | Concorrência da memória multiprocesso — trava `filelock` fail-closed, reload sob trava e modo somente-leitura | Accepted | 2026-10-28 |
| [0014](./docs/adrs/0014-sinal-duplo-de-erro.md) | Sinal duplo de erro — `isError` do protocolo mais o envelope estruturado (12 códigos) | Accepted | 2026-10-28 |
| [0015](./docs/adrs/0015-modo-privacidade-wallet-mask-values.md) | Modo privacidade `WALLET_MASK_VALUES` — allowlist fail-closed, tools monetárias indisponíveis | Accepted | 2026-10-28 |
| [0016](./docs/adrs/0016-validacao-de-payloads-em-tools-novas.md) | Regra de validação de payloads para tools novas — pydantic validate-then-passthrough | Accepted | 2026-10-28 |
| [0017](./docs/adrs/0017-cotacao-em-cache-vencido-nao-dispara-alerta.md) | Cotação em cache vencido não dispara alerta — `stale_quote` em `pending_check` | Accepted | 2026-10-28 |

## Learning Lessons

> Folder: `./docs/learning-lessons/`

- [get_asset_quote só cobre ações da B3 — FIIs, ETFs internacionais, cripto e tesouro retornam HTTP 410](./docs/learning-lessons/get_asset_quote_apenas_acoes_b3.md) — 2026-10-15
- [API upstream tem detalhe de proventos por ativo — o MCP só expõe o total agregado](./docs/learning-lessons/earnings_list_detalhe_proventos_por_ativo.md) — 2026-10-17
- [Efeito bola de neve: usar rendimento recorrente atual, nunca DY médio](./docs/learning-lessons/efeito_bola_de_neve_calculo.md) — 2026-10-17
- [Endpoints paginados podem ignorar `start`: proteja o merge com dedupe e guarda de progresso](./docs/learning-lessons/paginacao_merge_guardar_dedupe_e_progresso.md) — 2026-10-17
- [Endpoint de lançamentos existe: `/entries/{id}/{seção}` retorna compras/vendas ordem a ordem](./docs/learning-lessons/entries_endpoint_log_lancamentos.md) — 2026-10-26
- [Devin CLI `mcp add` tem flags de user scope e env — baseline do README estava incompleto](./docs/learning-lessons/devin_mcp_add_user_scope.md) — 2026-10-24
- [Formato real de plugin do Claude Code (versão instalada) diverge do publicado](./docs/learning-lessons/claude_plugin_formato_verificado.md) — 2026-10-24
- [filelock troca para soft lock em silêncio e cria o diretório pai — usar fallback_to_soft=False e guardar o diretório](./docs/learning-lessons/filelock_fallback_soft_silencioso.md) — 2026-10-28
- [FastMCP descarta o texto da docstring que vem depois do bloco `Args:` — regras de uso das tools não chegavam ao modelo](./docs/learning-lessons/fastmcp_docstring_descarta_texto_apos_args.md) — 2026-10-28
- [FastMCP: `mask_error_details` vem desligado e a exceção inesperada chega crua ao cliente — ligar a opção](./docs/learning-lessons/fastmcp_mask_error_details_padrao_falso.md) — 2026-10-28
- [Arquivo local: abrir por descritor com `O_NOFOLLOW`, num ponto só, e não arquivo por arquivo](./docs/learning-lessons/arquivo_local_abrir_por_fd_sem_seguir_link.md) — 2026-10-29
- [Um relógio só por decisão de frescor: monotônico dentro do processo, relógio de parede só na fronteira](./docs/learning-lessons/um_relogio_por_decisao_de_frescor.md) — 2026-10-29
- [`RecursionError` não é `ValueError`: profundidade de aninhamento é uma falha à parte do JSON malformado](./docs/learning-lessons/recursionerror_nao_e_valueerror.md) — 2026-10-29
- [Contador declarado pela fonte não é limite de laço: validar `total` antes de parar a paginação por ele](./docs/learning-lessons/contador_declarado_pela_fonte_nao_e_limite.md) — 2026-10-29
- [Um relatório que prova a ausência de um segredo não pode citá-lo: use `<id>` e uma checagem que lê o valor do ambiente](./docs/learning-lessons/relatorio_que_prova_ausencia_de_segredo_nao_o_cita.md) — 2026-10-31
