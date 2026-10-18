---
description: "Task list for feature implementation"
---

# Tasks: Agente de Investimentos conectado à Carteira Investidor10

**Input**: Design documents from `/specs/001-mcp-investidor10-wallet/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Tests**: Incluídos — o plano define pytest + respx como infra de testes (unit/contract/integration). Seguir TDD leve: testes primeiro quando indicado.

**Organization**: Tasks agrupadas por user story (P1→P3) para implementação e validação independentes.

**Layout do projeto** (flat, conforme plan.md): `server.py`, `wallet_client.py`, `memory_store.py` na raiz; `tests/{unit,contract,integration}/`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto Python

- [X] T001 Criar `pyproject.toml` com `fastmcp` e `httpx` pinados a versões publicadas há ≥7 dias (pesquisar versão atual no PyPI, sem ranges flutuantes), requires-python `>=3.11`, e dev-dependencies `pytest`, `pytest-asyncio`, `respx`; registrar `live` como marker do pytest
- [X] T002 Criar `.gitignore` com `.venv/`, `__pycache__/`, `memory.json`, `memory.json.tmp`, `memory.json.broken-*`, `.specify/feature.json`
- [X] T003 [P] Criar `README.md` com descrição do projeto, instalação via `uv sync`, execução `WALLET_ID=2061045 uv run server.py` e tabela das 19 tools (link para specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra compartilhada — cliente HTTP com cache/erros, store de memória base, esqueleto do servidor. BLOQUEIA todas as stories.

**⚠️ CRITICAL**: Nenhuma story começa antes desta fase completar.

- [X] T004 Implementar base de `wallet_client.py`: `httpx.AsyncClient` com `User-Agent: "Mozilla/5.0"` e timeout 20s; base URLs `https://investidor10.com.br/wallet/api/proxy/wallet-app` e `https://investidor10.com.br/api/rest`; `WALLET_ID` via env (default `2061045`)
- [X] T005 Adicionar cache TTL em memória a `wallet_client.py`: dict `chave=path+params → (timestamp, resposta)`, TTL via `WALLET_CACHE_TTL_SECONDS` (default 600); envelope de saída SEMPRE `{ "cached": bool, "fetched_at": ISO-8601, "data": ... }`; em falha da fonte com cache válido, retornar cache com `cached=true`, senão erro `source_unavailable`
- [X] T006 Adicionar normalização de erros a `wallet_client.py`: HTTP não-2xx/timeout → `source_unavailable`; JSON com schema inesperado (chaves-chave ausentes) → `unexpected_format`; nunca fabricar valores (FR-016); formato de erro único `{ "error": { "code": str, "message": str } }`
- [X] T007 Implementar base de `memory_store.py`: schema v1 de `memory.json` exatamente como data-model.md (chaves `version`, `wallet_goal`, `theses`, `rules`, `decisions`, `insights_log`, `alerts`); cria arquivo vazio na 1ª execução; path via `WALLET_MEMORY_PATH` (default `./memory.json`); IDs inteiros monotônicos por coleção (`max(id)+1`); timestamps ISO-8601 com timezone local
- [X] T008 Adicionar a `memory_store.py`: escrita atômica (serializar → `memory.json.tmp` → `os.replace`); modo degradado — JSON inválido ou `version > 1` → store em modo `memory_unavailable` SEM crash, preservando arquivo original como `.broken-<timestamp>` antes de qualquer reescrita (research D6)
- [X] T009 Criar esqueleto de `server.py`: app `FastMCP("investidor10-wallet")`, instância única do memory store carregada no startup, `if __name__ == "__main__": mcp.run()` (stdio); helper compartilhado para envelopar retornos de tools de dados (reusa T005/T006)
- [X] T010 [P] Testes unitários do store em `tests/unit/test_memory_store.py`: CRUD básico por coleção (read PRIMEIRO, devem falhar/endurecer T007/T008), escrita atômica (sem arquivo parcial em falha simulada), corrupção → modo degradado sem exceção e com backup `.broken-*`, `version > 1` → degradado

**Checkpoint**: `uv run server.py` sobe sem erro; `uv run pytest tests/unit/test_memory_store.py` passa. Stories desbloqueadas.

---

## Phase 3: User Story 1 — Visão completa da carteira sob demanda (Priority: P1) 🎯 MVP

**Goal**: Agente responde "como está minha carteira?" com resumo, alocação e posições das 5 classes, valores idênticos à fonte.

**Independent Test**: No cliente MCP, perguntar "qual o resumo da minha carteira?" e conferir números contra a página pública da carteira para TODAS as classes (SC-001, SC-002); segunda consulta consecutiva deve indicar cache (FR-014).

### Tests for User Story 1

> Escrever PRIMEIRO, verificar que FALHAM antes da implementação.

- [X] T011 [P] [US1] Testes de unidade do cache e erros do cliente em `tests/unit/test_wallet_client.py` com respx: hit de cache dentro do TTL (2ª chamada não bate na rede, `cached=true`), expiração do TTL, `source_unavailable` em timeout SEM cache válido, `unexpected_format` em payload sem chaves-chave
- [X] T012 [P] [US1] Testes de contrato das tools de carteira em `tests/contract/test_tools_schemas.py` com respx: envelope `{cached, fetched_at, data}` presente em resumo/alocação/posições; `get_wallet_positions("Ticker")` retorna posições com `average_price`, `percent_wallet`, `percent_ideal`; `get_wallet_positions("Bitcoin")` → erro `invalid_asset_type` listando `Ticker|Fii|EtfInternational|Treasure|Crypto`; classe vazia → `data: []` sem erro

### Implementation for User Story 1

- [X] T013 [US1] Adicionar `get_summary(wallet_id)` a `wallet_client.py`: `GET /summary/metrics/{WALLET_ID}?type=without-earnings&raw=1`, passthrough do payload no envelope (aplicado, equity, variação, TWR total e 12M)
- [X] T014 [P] [US1] Adicionar `get_allocation(wallet_id)` a `wallet_client.py`: `GET /summary/donutchart/{WALLET_ID}/all?groupBy=ticker` (alocação por ativo/classe)
- [X] T015 [P] [US1] Adicionar `get_positions(wallet_id, asset_type)` a `wallet_client.py`: validar `asset_type ∈ {Ticker, Fii, EtfInternational, Treasure, Crypto}` (case-sensitive da API; normalizar input do usuário para esses valores, senão `invalid_asset_type`); `GET /summary/actives/{WALLET_ID}/{asset_type}?raw=1&api_version=v2&start=0&length=50&order_column=equity_total&order_dir=desc`
- [X] T016 [US1] Registrar em `server.py` tools `get_wallet_summary()`, `get_wallet_allocation()`, `get_wallet_positions(asset_type)` com docstrings em inglês explicando quando usar, parâmetros e campos de retorno (research D8: docstring é o contrato com o modelo); indicadores não aplicáveis por classe são omitidos, nunca inventados; docstring de posições deve instruir o modelo a sinalizar que equity de `EtfInternational` envolve conversão cambial (US1 cenário 3)
- [X] T017 [US1] Teste de integração live opt-in em `tests/integration/test_live_api.py` (marker `live`): as 3 tools contra a carteira real `2061045` — resumo retorna equity > 0; posições das 5 classes retornam sem erro (algumas podem ser `[]`)

**Checkpoint**: SC-001 (<30s por pergunta) e SC-002 (100% dos valores conferem com a fonte) validáveis no cliente. MVP pronto.

---

## Phase 4: User Story 2 — Insights de rebalanceamento e aporte (Priority: P2)

**Goal**: Agente identifica desvios `% atual vs % ideal` por ativo/classe e sugere aportes cruzando distância do ideal + flag `buy` da fonte.

**Independent Test**: Perguntar "quais ativos estão acima do peso ideal?": resposta corresponde exatamente à diferença entre `percent_wallet` e `percent_ideal` de cada ativo (precisão 0,1 p.p., SC-003), incluindo o caso conhecido de PETR4 (15,2% vs 8%).

> Nota de design (contracts FR-007): o cruzamento é feito pelo MODELO sobre os dados das tools da US1 — não há tool nova de rebalanceamento. Esta fase garante que os dados necessários chegam completos e que as docstrings orientam o modelo.

### Tests for User Story 2

- [X] T018 [P] [US2] Estender `tests/contract/test_tools_schemas.py`: fixture de posições (respx) DEVE conter `percent_wallet`, `percent_ideal` e flag `buy` em cada posição — teste falha se algum campo for descartado no passthrough (proteção contra o servidor "ajudar demais" filtrando payload)

### Implementation for User Story 2

- [X] T019 [US2] Revisar e endurecer docstrings de `get_wallet_positions` e `get_wallet_allocation` em `server.py`: instruir explicitamente o modelo a comparar `percent_wallet` vs `percent_ideal` ordenando por magnitude do desvio, priorizar aportes em ativos abaixo do ideal com `buy` positivo, e nunca sugerir vendas não solicitadas
- [X] T020 [US2] Validação manual ponta a ponta (cenário quickstart Story 2): desvios com precisão de 0,1 p.p. (SC-003); carteira alinhada ao ideal → agente declara ausência de desvios sem forçar sugestões

**Checkpoint**: Análises de rebalanceamento corretas a partir de dados 100% passthrough.

---

## Phase 5: User Story 3 — Memória de longo prazo e contexto do investidor (Priority: P2)

**Goal**: Agente persiste teses, regras, objetivo, decisões com desfecho e log de insights; carrega tudo deterministicamente no início de cada sessão.

**Independent Test**: Registrar tese+decisão numa sessão, encerrar, abrir nova sessão: agente recupera o contexto citando datas (SC-004) via `get_session_context`; recomendação recusada não reaparece sem novo fundamento (FR-010).

> Decisão de design (research D4/D5): memória é subsistema do PRÓPRIO servidor (não MCP separado), persistida em `memory.json` v1.

### Tests for User Story 3

> Escrever PRIMEIRO, verificar que FALHAM antes da implementação.

- [X] T021 [P] [US3] Estender `tests/unit/test_memory_store.py`: `save_thesis` valida ticker uppercase e texto não vazio; múltiplas teses por ticker com histórico; `log_decision` cria com `outcome="pending"` e `kind ∈ {recommendation, user_decision}`; `record_decision_outcome` grava `outcome_at` e só aceita `accepted|rejected|postponed`; `log_insight` com `fingerprint` duplicado retorna `already_logged=true` SEM duplicar entrada (SC-005)
- [X] T022 [P] [US3] Estender `tests/contract/test_tools_schemas.py`: `get_session_context` retorna `{memory: {...}, triggered_alerts: [...], memory_status: "ok"|"unavailable"}`; com memory corrompida, `memory_status="unavailable"` e as demais tools continuam respondendo

### Implementation for User Story 3

- [X] T023 [US3] Implementar em `memory_store.py` operações: get/set `wallet_goal`; CRUD de `theses` (campos `id, ticker, text, created_at, updated_at`); CRUD de `rules` (`id, text, created_at`); `decisions` com máquina de desfecho (`outcome: pending → accepted|rejected|postponed`, gravando `outcome_at`); `insights_log` com dedupe por `fingerprint`
- [X] T024 [US3] Registrar em `server.py` tools `get_wallet_goal()`, `set_wallet_goal(text)`, `save_thesis(ticker, text)`, `get_theses(ticker=None)`, `save_rule(text)`, `get_rules()`, `log_decision(kind, content, ticker=None, rationale=None)`, `record_decision_outcome(decision_id, outcome, note=None)`, `log_insight(kind, fingerprint, summary)` — ids inexistentes → erro `not_found`; parâmetros inválidos → `invalid_params`; docstrings em inglês orientando o modelo a registrar decisões e desfechos (FR-008, FR-010)
- [X] T025 [US3] Registrar em `server.py` a tool `get_session_context()`: retorna digest completo (objetivo, teses por ticker, regras, decisões pendentes, insights recentes) + `memory_status`; docstring DEVE dizer "chamar obrigatoriamente no início de cada sessão" (FR-009); nesta fase, `triggered_alerts: []` (avaliação real vem na US6, dependente de cotações)

**Checkpoint**: Dois chats consecutivos comprovam persistência (SC-004) e dedupe de insights (SC-005).

---

## Phase 6: User Story 4 — Cotações e fundamentos em tempo quase real (Priority: P2)

**Goal**: Agente consulta cotação, variações, valuation (Graham/Bazin), P/L, P/VP, DY e setor de qualquer ticker, sinalizando defasagem da fonte.

**Independent Test**: Perguntar cotação de um ticker conhecido e conferir valores com a fonte no mesmo momento; defasagem (~15 min B3) sempre declarada (SC-007); `VALE99` → erro claro de não encontrado.

### Tests for User Story 4

- [X] T026 [P] [US4] Estender `tests/contract/test_tools_schemas.py`: `get_asset_quote("PETR4")` (respx) retorna preço/variações/Graham/Bazin/DY/setor no envelope; ticker inexistente (HTTP 404 ou payload vazio da fonte) → erro `ticker_not_found`; input `" petr4 "` é normalizado (trim+upper)

### Implementation for User Story 4

- [X] T027 [US4] Adicionar `get_quote(ticker)` a `wallet_client.py`: `GET /api/rest/assets/tickers/{ticker}` (base URL REST, não o proxy wallet); normalizar ticker (trim+upper); 404/vazio → `ticker_not_found` com sugestão de verificar grafia
- [X] T028 [US4] Registrar em `server.py` tool `get_asset_quote(ticker)` com docstring em inglês: declarar defasagem inerente da fonte (~15 min B3), instruir o modelo a SEMPRE informar `cached`/`fetched_at` ao usuário (FR-014), e a cruzar cotação com preço médio da posição quando o ativo estiver na carteira (chamando `get_wallet_positions`)
- [X] T029 [US4] Estender `tests/integration/test_live_api.py` (marker `live`): `get_asset_quote("PETR4")` retorna preço > 0 contra a API real

**Checkpoint**: SC-007 validável no cliente (cotação com defasagem declarada; erro claro para ticker inválido).

---

## Phase 7: User Story 5 — Renda passiva e evolução patrimonial (Priority: P3)

**Goal**: Agente apresenta proventos por período (default 12M) e evolução mensal do patrimônio separando aplicado de ganho de capital.

**Independent Test**: Pedir proventos de período conhecido e conferir o total com a fonte para as mesmas datas (SC-002); período invertido → agente questiona/corrige, nunca vazio silencioso.

### Tests for User Story 5

- [X] T030 [P] [US5] Estender `tests/contract/test_tools_schemas.py`: `get_earnings()` sem datas → últimos 12 meses; `get_earnings("2026-10-01", "2026-01-01")` → erro `invalid_params` indicando inversão; `get_patrimony_history(0)` e `(-3)` → `invalid_params`; período sem proventos → `data` com total zero/vazio SEM erro

### Implementation for User Story 5

- [X] T031 [P] [US5] Adicionar `get_earnings(wallet_id, start_date=None, end_date=None)` a `wallet_client.py`: `GET /earnings/total-period/{WALLET_ID}?start_date=...&end_date=...`; validar formato `YYYY-MM-DD`; omitidas → últimos 12 meses; `start_date > end_date` → `invalid_params` sugerindo correção (nunca retorno silencioso)
- [X] T032 [P] [US5] Adicionar `get_patrimony_history(wallet_id, months)` a `wallet_client.py`: `GET /summary/barchart/{WALLET_ID}/{months}/all`; `months` inteiro > 0, senão `invalid_params` com exemplos (12, 24, 60)
- [X] T033 [US5] Registrar em `server.py` tools `get_earnings(start_date=None, end_date=None)` e `get_patrimony_history(months)` com docstrings em inglês: instruir o modelo a apresentar série separando aporte de valorização, a calcular YOC por ativo cruzando proventos com preço médio das posições, e a SEMPRE informar `cached`/`fetched_at` ao usuário (FR-014)

**Checkpoint**: Totais de proventos conferem com a fonte (SC-002); evolução patrimonial parametrizável.

---

## Phase 8: User Story 6 — Alertas de preço e relatórios enriquecidos (Priority: P3)

**Goal**: Alertas de preço registrados pelo usuário disparam deterministicamente na abertura da próxima sessão (sem repetição); relatórios combinam dados quantitativos + web.

**Independent Test**: Criar alerta com condição já satisfeita, abrir nova sessão: alerta entregue no início com data de registro e preço atual, marcado `triggered`, e NÃO reaparece na sessão seguinte (SC-006).

> Dependência: avaliação de alertas usa cotações (US4) dentro de `get_session_context` (US3). Pesquisa web dos relatórios é capability do próprio cliente — o servidor fornece os dados quantitativos (contracts FR-012).

### Tests for User Story 6

> Escrever PRIMEIRO, verificar que FALHAM antes da implementação.

- [X] T034 [P] [US6] Criar `tests/unit/test_alerts.py`: `direction=below` dispara quando `preço_atual <= limit_price`; `direction=above` quando `>=` (fronteira inclusiva); transição `active → triggered` grava `triggered_at` e `triggered_price` e é TERMINAL (2ª avaliação não redispara — SC-006); `active → cancelled` terminal; `limit_price <= 0` e `direction` inválida → `invalid_params`

### Implementation for User Story 6

- [X] T035 [US6] Implementar em `memory_store.py` operações de `alerts`: `create_price_alert(ticker, direction, limit_price)` (state inicial `active`; `direction ∈ {above, below}`, `limit_price > 0`); `list_price_alerts(state=None)`; `cancel_price_alert(alert_id)` (só de `active`; já `triggered`/`cancelled` → `invalid_params`; inexistente → `not_found`); `evaluate_alerts(quotes: dict)` aplicando a máquina de estados do data-model.md
- [X] T036 [US6] Integrar avaliação a `get_session_context()` em `server.py`: para cada alerta `active`, buscar cotação via `get_quote` (reusando cache — 1 chamada por ticker no máximo), avaliar condição, persistir disparos e retornar em `triggered_alerts` com preço atual e data de registro; falha na cotação de um ticker NÃO aborta o bootstrap (alerta daquele ticker fica `active` com nota de verificação pendente)
- [X] T037 [US6] Registrar em `server.py` tools `create_price_alert(ticker, direction, limit_price)`, `list_price_alerts(state=None)`, `cancel_price_alert(alert_id)` com docstrings em inglês esclarecendo que o disparo ocorre na abertura de sessão (sem monitoramento contínuo — escopo da spec)
- [X] T038 [US6] Atualizar docstring de `get_asset_quote`/`get_wallet_positions` em `server.py` orientando geração de relatórios: combinar posição + indicadores + busca web do cliente, citar fontes, e declarar explicitamente ausência de notícias relevantes em vez de conteúdo genérico (cenário 3 da Story 6)

**Checkpoint**: SC-006 validável: disparo único, na abertura, sem duplicados (cenário quickstart Story 6).

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Acabamento e validação integral

- [X] T039 [P] Completar `README.md`: configuração nos clientes (Claude Desktop JSON, `claude mcp add`, Devin CLI), env vars (`WALLET_ID`, `WALLET_MEMORY_PATH`, `WALLET_CACHE_TTL_SECONDS`), avisos de risco (API interna não documentada, delay B3, uso pessoal/educacional)
- [X] T040 [P] Revisão de erros: garantir que TODAS as tools retornam apenas envelope `{cached, fetched_at, data}` ou `{error: {code, message}}` — varredura em `server.py`/`wallet_client.py` contra contracts/mcp-tools.md
- [X] T041 Executar validação integral de `quickstart.md`: todos os cenários das 6 stories + edge cases (memória corrompida, rede fora) em um cliente MCP real
- [X] T042 Rodar `uv run pytest` completo (unit + contract) e `uv run pytest -m live` para regressão final

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato
- **Foundational (Phase 2)**: depende de Setup — **BLOQUEIA** todas as stories
- **Stories (Phase 3–8)**: dependem de Foundational
- **Polish (Phase 9)**: depende das stories desejadas

### User Story Dependencies

- **US1 (P1)**: sem dependência de outras stories — MVP
- **US2 (P2)**: usa dados das tools da US1 (docstrings/passthrough), mas entrega independente
- **US3 (P2)**: usa apenas Foundational (memory_store base) — independente
- **US4 (P2)**: independente
- **US5 (P3)**: independente
- **US6 (P3)**: depende de US4 (cotações) e US3 (`get_session_context`) para a avaliação de alertas

### Parallel Opportunities

- T003 ∥ T001/T002; T010 escrito PRIMEIRO e roda ∥ T004–T009 — TDD puro: os testes falham até T007/T008 existirem e então endurecem a base
- Após Foundational: **US1, US3, US4 podem rodar em paralelo** (arquivos distintos: wallet_client funções novas ∥ memory_store operações)
- Dentro de cada story: tasks de teste marcadas [P] entre si; T013/T014/T015 [P]; T031/T032 [P]
- US6 só após US3+US4

### Parallel Example: pós-Foundational

```bash
# Trilha A (US1): T011, T012 [P] → T013, T014, T015 [P] → T016 → T017
# Trilha B (US3): T021, T022 [P] → T023 → T024 → T025
# Trilha C (US4): T026 → T027 → T028 → T029
# Depois: US5 ∥ qualquer restante; US6 por último; Polish
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + 2 (setup + foundational)
2. Phase 3 (US1) → **STOP**: validar "como está minha carteira?" no cliente contra a página pública
3. Agente já responde a visão completa da carteira

### Incremental Delivery (ordem recomendada)

1. US1 (visão) → MVP ✅
2. US3 (memória) — **priorizar sobre US2**: é o diferencial do produto declarado pelo usuário (P2, "imprescindível")
3. US2 (rebalanceamento) — fina, sobre dados já entregues
4. US4 (cotações) → desbloqueia US6
5. US5 (renda/patrimônio)
6. US6 (alertas + relatórios)
7. Polish + validação quickstart

---

## Notes

- [P] = arquivos diferentes, sem dependência de tasks incompletas
- Insights (rebalanceamento, relatórios) são gerados pelo MODELO — o servidor garante dados completos + docstrings orientadoras (D8); não criar tools de "insight" no servidor
- Nunca fabricar valores em falha da fonte (FR-016) — erro estruturado sempre
- Docstrings em inglês em TODAS as tools (são a interface com o LLM); interação com o usuário permanece pt-BR
- Commit após cada fase/checkpoint

---

## Fixes do SDD Final Review — ciclo 2 (2026-10-17)

- [X] C2-1 Rejeitar IDs ausentes/duplicados por coleção no load de `memory_store.py` (arquivo degrada com backup, sem sobrescrever o original)
- [X] C2-2 Persistir todos os alertas satisfeitos em UMA gravação atômica em `evaluate_alerts` (falha na gravação não perde notificação — ADR-0002)
- [X] C2-3 Conter limites numéricos malformados/oversized: helper `alert_is_valid` compartilhado; bootstrap reporta `invalid_alert` sem exceção crua
- [X] C2-4 Validar tipos aninhados das respostas da fonte antes de cachear (`positions.data` lista, `earnings.sum` numérico) → `unexpected_format`
- [X] C2-5 Servir cache expirado com idade explícita em HTTP 5xx (além de erros de transporte); 4xx continua erro explícito
- [X] C2-6 Paginar `get_wallet_positions` em lotes de 50 até `total` (critério 100% dos ativos)
- [X] C2-7 Payload vazio em `get_asset_quote` → `ticker_not_found` (T026); datas estritas `YYYY-MM-DD`; `WALLET_ID` numérico
- [X] C2-8 Hardening de segurança: backup `.broken-*` com permissões 0600 (O_EXCL)
- [X] C2-9 Documentar: contrato atualizado (paginação, pending_check, quote vazio, datas) e ADR-0002 criado
- [X] C2-10 Testes de regressão: 162 unit/contract + 3 live, cobertura 97%

---

## Fixes do SDD Final Review — ciclo 3 (2026-10-17)

- [X] C3-1 `get_summary`: `applied`/`equity` validados como numéricos (número finito ou string numérica finita — a fonte live envia strings; bool não conta) — presente mas inválido → `unexpected_format` sem cachear; teste de contrato com `{"applied": "not-a-number", "equity": 1000}` (fecha item obrigatório 4 do ciclo 2)
- [X] C3-2 Paginação `get_positions`: dedupe por ticker (identidade da linha como fallback), parada em página sem progresso/curta/`total` atingido, teto fixo de 20 páginas removido, `merged["total"]` = linhas únicas coletadas; testes: fonte ignora `start`, sobreposição parcial, classe com 1050 posições, `total` ausente
- [X] C3-3 Política de cache 5xx registrada no ADR-0003: bound `WALLET_CACHE_MAX_STALE_SECONDS` (default 86400) — entrada mais antiga → `source_unavailable`; testes de transporte e 503 dentro/fora do bound
- [X] C3-4 Startup estruturado: `WALLET_ID` não numérico ou `WALLET_CACHE_TTL_SECONDS`/`WALLET_CACHE_MAX_STALE_SECONDS` inválidos → `SystemExit` com mensagem acionável, sem traceback; testes subprocess env-driven
- [X] C3-5 `get_quote`: apenas payload genuinamente vazio (`{}`) → `ticker_not_found`; shape errada não vazia (array/null/string/número) → `unexpected_format`; testes para ambos
- [X] C3-6 Ticker inválido persistido (regex) → `{"alert_id", "reason": "invalid_alert"}` via `TICKER_PATTERN` compartilhado entre `create_price_alert` e `alert_is_valid`; testes unit + contrato (lowercase continua válido)
- [X] C3-7 Documentar: ADR-0003 criado; contrato atualizado (envelope 5xx, summary, paginação, quote); README com `WALLET_CACHE_MAX_STALE_SECONDS`
- [X] C3-8 Testes de regressão: unit/contract completos + live + cobertura
