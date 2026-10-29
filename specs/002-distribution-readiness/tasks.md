# Tasks: Prontidão para distribuição do produto (Fase 0 do ROADMAP)

**Input**: Design documents from `/specs/002-distribution-readiness/`

**Prerequisites**: plan.md, spec.md, research.md (D1–D9), data-model.md, contracts/packaging-and-config.md (C1–C7), quickstart.md (S1–S8)

**Tests**: Incluídas — o projeto tem suíte pytest/respx viva e o plan.md prescreve cobertura nova (test_bootstrap.py, probe, live). Testes são escritos PRIMEIROS e devem FALHAR antes da implementação.

**Organization**: Tarefas agrupadas por user story (US1–US4 da spec.md) com fases Setup/Foundational/Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: US1–US4 mapeadas da spec.md
- Caminhos relativos à raiz do repositório

---

## Phase 1: Setup (Reestruturação para pacote instalável)

**Purpose**: src layout (research D1/D2) — pré-requisito físico de todo o resto do ciclo

- [x] T001 Mover `server.py`, `wallet_client.py`, `memory_store.py` para `src/investidor10_wallet/` com imports relativos de pacote (`from . import wallet_client` etc.) e criar `src/investidor10_wallet/__init__.py` com `__version__ = "0.1.0"` (fonte única de versão, research D6/data-model Release)
- [x] T002 Atualizar `pyproject.toml`: `[build-system]` hatchling, versão dinâmica lida de `investidor10_wallet.__version__`, `[project.scripts] mcp-investidor10-wallet = "investidor10_wallet.server:main"`, `readme = "README.md"`, licença/classifiers/requires-python>=3.11; rodar `uv lock` (research D1)
- [x] T003 Ajustar imports dos testes `tests/unit/`, `tests/contract/`, `tests/integration/` para o pacote (`from investidor10_wallet import memory_store, wallet_client` etc.) e setar `pythonpath = ["src"]` em `[tool.pytest.ini_options]` do `pyproject.toml`; suíte inteira verde sem mudança de comportamento
- [x] T004 [P] Adicionar config do `ruff` (lint + format) em `pyproject.toml` e incluir `ruff` e `pre-commit` nos dev deps pinados (≥7 dias, política ADR-0001 §4); `uv lock`
- [x] T005 Rodar `ruff format` uma vez sobre todo o código e corrigir achados de `ruff check`; suíte verde (registrar como mudança interna no changelog em T010, research D7)

**Checkpoint**: `uv sync` instala o pacote editável; `uv run pytest` verde no novo layout

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ponto de entrada e esqueleto de bootstrap que todas as stories consomem

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T006 Criar `src/investidor10_wallet/bootstrap.py` com os esqueletos de mensagem PT-BR operador-facing do contrato C6 (sem WALLET_ID / carteira não encontrada ou privada / falha de migração / conflito resolvido) e helper de emissão para **stderr** (stdout é reservado ao protocolo MCP — restrição do plan.md)
- [x] T007 Criar `main()` em `src/investidor10_wallet/server.py` chamando as etapas de bootstrap na ordem determinística do contrato C3 (config → path da memória → store → probe → serve) como esqueleto injetável, e `mcp.run()` ao final; garantir que todo o parsing de env (`WALLET_ID`, TTLs, `WALLET_MEMORY_PATH`) deixa de ocorrer em import-time e passa a ocorrer dentro de `main()`/bootstrap **antes** da criação do app FastMCP (research D3)

**Checkpoint**: wheel construído (`uv build`) instala num venv limpo e `mcp-investidor10-wallet` sobe/serva; comportamento das 19 tools inalterado (FR-010)

---

## Phase 3: User Story 2 — O produto nunca opera com a carteira de outra pessoa (Priority: P1)

**Goal**: `WALLET_ID` obrigatório; nenhum default pessoal; falha de startup imediata e acionável em PT-BR, sem chamadas de rede

**Independent Test**: `env -u WALLET_ID <console script>` → exit 1 com mensagem PT-BR nomeando a variável e a URL pública; zero egresso de rede (quickstart S3)

### Tests for User Story 2 ⚠️ (escrever primeiro, devem FALHAR)

- [x] T008 [P] [US2] Testes unitários em `tests/unit/test_bootstrap.py`: `WALLET_ID` ausente e vazio → `SystemExit` código 1 com mensagem PT-BR contendo "WALLET_ID" e "investidor10.com.br/carteira"; valor não numérico → `SystemExit` (mantém ADR-0003 §3)
- [x] T009 [P] [US2] Teste em `tests/unit/test_bootstrap.py` provando **zero chamadas de rede** na falha de config (respx com `assert_all_called=False` rota não registrada / spy) — SC-002

### Implementation for User Story 2

- [x] T010 [US2] Remover o default `"<id>"` de `src/investidor10_wallet/wallet_client.py` e mover a validação de `WALLET_ID` (ausente/vazio/não-numérico) para `bootstrap.py` usando os esqueletos C6; validação executada antes da criação do app FastMCP (research D3, contrato C2)
- [x] T011 [US2] Varrer o repositório e substituir `<id>` hardcoded fora dos testes por placeholder (`<id>`) em `README.md` e demais docs citados; nos testes, manter apenas onde o ID é parte do cenário (não é default)

**Checkpoint**: US2 validada por S3 — servidor aborta sem carteira configurada em < 1s, sem rede

---

## Phase 4: User Story 1 — Instalação e execução em uma linha, sem clonar repositório (Priority: P1) 🎯 MVP

**Goal**: pacote constrói, instala e serve via executor de pacotes sob demanda; versão única com changelog

**Independent Test**: clean venv recebe o wheel de `uv build`, console script roda e serve stdio sem nenhum checkout de código (quickstart S1/S8)

### Tests for User Story 1 ⚠️ (escrever primeiro)

- [x] T012 [P] [US1] Teste de contrato de empacotamento em `tests/contract/test_packaging_contract.py`: `investidor10_wallet.server:main` importável; `__version__` casa com a versão declarada no `pyproject.toml`; nenhum módulo de topo (`server`, `wallet_client`, `memory_store`) exportado sem o prefixo do pacote (contrato C1)

### Implementation for User Story 1

- [x] T013 [US1] Validar o artefato real: `uv build` → instalar o wheel num venv limpo → `python -c "import investidor10_wallet"` e console script sem `WALLET_ID` sai com exit 1 PT-BR (smoke test do quickstart S8; registrar gaps encontrados como follow-ups)
- [x] T014 [US1] Criar `CHANGELOG.md` na raiz (Keep a Changelog, PT-BR) com `## [0.1.0]` cobrindo: empacotamento/console script, `WALLET_ID` obrigatório, path canônico da memória + migração, validação de carteira no startup, onboarding, gates (contrato C7, FR-008)

**Checkpoint**: US1+US2 juntas = MVP publicável (pacote funciona sem clone e não vaza carteira alheia)

---

## Phase 5: User Story 3 — Memória confiável e compartilhada entre todos os clientes (Priority: P2)

**Goal**: default canônico `~/.investidor10/memory.json`; migração sem perda do legado `./memory.json`; todos os clientes convergem para o mesmo arquivo

**Independent Test**: regra salva num cliente aparece em outro cliente sem configuração extra (quickstart S2); três cenários de migração de S5

### Tests for User Story 3 ⚠️ (escrever primeiro, devem FALHAR)

- [x] T015 [P] [US3] Testes unitários em `tests/unit/test_bootstrap.py` (tmp dirs + monkeypatch de `HOME`/cwd) cobrindo a máquina de estados do data-model: `OVERRIDE` (`WALLET_MEMORY_PATH` definido → usa, sem migração), `NOVO_CANONICO` (nada existe → canônico), `MIGRADO` (só legado → dir 0700, arquivo 0600, conteúdo idêntico por diff, legado removido), `CANONICO_WINS` (ambos → canônico usado, legado renomeado `memory.json.legacy-<YYYYMMDD-HHMMSS>`, aviso no stderr) — contrato C4
- [x] T016 [P] [US3] Teste em `tests/unit/test_bootstrap.py`: falha de migração (destino não gravável) → `SystemExit` PT-BR nomeando o caminho tentado e **legado intocado** (contrato C4/C6)

### Implementation for User Story 3

- [x] T017 [US3] Implementar `resolve_memory_path()` e a migração em `src/investidor10_wallet/bootstrap.py`: cópia atômica temp 0600 + `os.replace` do legado para `~/.investidor10/memory.json`, verificação de conteúdo antes da remoção, rename com timestamp no conflito, avisos stderr (research D5) — mesma arquivo que T010: sequencial após US2 se houver um único executor
- [x] T018 [US3] Conectar em `src/investidor10_wallet/server.py`: `MemoryStore(path_resolvido)` substituindo `os.getenv("WALLET_MEMORY_PATH", "memory.json")`; semântica do store/schema intocada (ADR-0002)
- [x] T019 [US3] Migrar o `./memory.json` real do autor na primeira execução da versão nova e verificar o cenário S5 (diff idêntico, permissões 0700/0600)

**Checkpoint**: US3 validada — memória converge entre clientes e migração preserva 100% das coleções (SC-005)

---

## Phase 6: User Story 4 — Primeira execução guiada e sem armadilhas (Priority: P2)

**Goal**: carteira validada no startup com erros amigáveis PT-BR; README-onboarding que leva o usuário novo até sessão funcionando

**Independent Test**: S4 (404 → exit 1 PT-BR; fonte fora → warning + servidor sobe) e caminho do README até sessão real (quickstart S1)

### Tests for User Story 4 ⚠️ (escrever primeiro, devem FALHAR)

- [x] T020 [P] [US4] Testes unitários do probe em `tests/unit/test_bootstrap.py` (respx): 200→segue; 404→`SystemExit` PT-BR "não encontrada ou não é pública"; 401/403→`SystemExit` PT-BR carteira privada; 5xx/timeout→warning no stderr e **startup continua** — tabela do contrato C5
- [x] T021 [P] [US4] Teste live em `tests/integration/test_live_api.py` (marker `live`): ID inexistente (`99999999999`) → 404 no probe — vigia drift da classificação (research D4)

### Implementation for User Story 4

- [x] T022 [US4] Implementar `validate_wallet()` em `src/investidor10_wallet/wallet_client.py`: GET `/summary/metrics/{WALLET_ID}` com headers de browser, timeout 10s e a classificação do contrato C5 (research D4; evidência live 18/10/2026 já confirmada)
- [x] T023 [US4] Conectar o probe no `main()` de `src/investidor10_wallet/server.py` após validação de config e antes de servir (ordem C3); garantir invariantes: zero egresso antes do probe, nada no stdout
- [x] T024 [P] [US4] Reescrever `README.md` como onboarding PT-BR com as seções da research D8: intro+aviso API não documentada, instalação 1 linha `uvx`, como obter `WALLET_ID` na URL pública, exigência de carteira pública, config por cliente com **caminho absoluto do `uv`** para GUI macOS (`which uv`), tabela de troubleshooting ("MCP failed to connect" → PATH), env overrides e local da memória `~/.investidor10/` (FR-006/FR-007)
- [x] T025 [P] [US4] Escrever `docs/adrs/0009-idioma-das-mensagens-operador-vs-modelo.md` consolidando a regra bootstrap PT-BR / tools EN (research D9) e indexar no `CLAUDE.md` tabela de ADRs

**Checkpoint**: US4 validada — novo usuário segue o README até sessão funcionando; falhas de config auto-diagnosticáveis (SC-001/SC-004)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Gates de qualidade, pipeline de release e fechamento de ciclo (research D6/D7, FR-008/FR-009)

- [x] T026 [P] Criar `.pre-commit-config.yaml` com hooks `ruff` (lint) e `ruff-format` pinados (≥7 dias) e rodar `pre-commit run --all-files` verde (FR-009)
- [x] T027 [P] Criar `.github/workflows/ci.yml`: matriz Python 3.11/3.12/3.13 × ubuntu-latest/macos-latest, `uv sync --locked`, `pytest` (não-live), `ruff check`, `ruff format --check` (research D7; testes live ficam fora — action semanal é Fase 1)
- [x] T028 Criar `.github/workflows/release.yml` gatilhado por tag `v*`: `uv build` → smoke test do wheel em venv limpo (import + console script sem `WALLET_ID` exit 1 PT-BR) → gate da seção do changelog → publish PyPI via trusted publishing OIDC (contrato C7)
- [x] T029 [P] Atualizar `docs/ROADMAP.md` marcando os itens da Fase 0 entregues e referenciar spec 002; conferir que `.gitignore` cobre artefatos novos (nada a adicionar para `~/.investidor10/` — fora do repo)
- [x] T030 Executar a validação completa do `quickstart.md` (S1–S8) e registrar resultados em `reports/002-distribution-readiness-validation.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — começa imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as stories
- **US2 (Phase 3)** e **US1 (Phase 4)**: após Foundational; sem dependência mútua (arquivos distintos: bootstrap/wallet_client vs. pyproject/changelog)
- **US3 (Phase 5)**: após Foundational; toca `bootstrap.py` (mesmo arquivo de T010/US2) — sequencial após US2 com um único executor
- **US4 (Phase 6)**: após Foundational; toca `wallet_client.py` e `server.py` (T010/T013 os tocam também) — sequencial após US2/US4-probe wiring; docs (T024/T025) são paralelizáveis
- **Polish (Phase 7)**: após todas as stories desejadas

### User Story Dependencies

- **US2 (P1)**: só Foundational — segurança mínima antes de qualquer publicação
- **US1 (P1)**: só Foundational — mas **MVP público = US1 + US2 juntas** (publicar com o default pessoal seria ativamente danoso)
- **US3 (P2)**: só Foundational — pré-requisito de produto para o `uvx` ter valor real (default relativo quebra sem repo dir)
- **US4 (P2)**: só Foundational — docs podem correr em paralelo à implementação

### Parallel Opportunities

- T004 (ruff config) paralela a T001–T003 (arquivos diferentes do código movido)
- T008/T009 (testes US2) paralelos entre si; T015/T016 (US3) paralelos; T020/T021 (US4) paralelos; T024/T025 (docs/ADR) paralelos a T022/T023
- T026/T027 (pre-commit/CI) e T029 paralelos no Polish
- Stories em sequência com um único executor: US2 → US1 → US3 → US4 (prioridade), com docs de US4 podendo adiantar-se

---

## Parallel Example: User Story 3

```bash
# Escrever juntos (arquivos de teste distintos/independentes):
Task: "[US3] Testes resolução/migração 4 estados em tests/unit/test_bootstrap.py (T015)"
Task: "[US3] Teste falha de migração legado intacto em tests/unit/test_bootstrap.py (T016)"

# Implementação sequencial (mesmo arquivo bootstrap.py):
Task: "[US3] resolve_memory_path() + migração (T017)" → Task: "[US3] wire em server.py (T018)"
```

---

## Implementation Strategy

### MVP First (US2 + US1 — ambas P1)

1. Setup (T001–T005) + Foundational (T006–T007)
2. US2 (T008–T011): sem carteira alheia embutida
3. US1 (T012–T014): pacote funciona de uma linha
4. **STOP**: só aqui o pacote pode ser publicado (US1 sem US2 não vai a público)

### Incremental Delivery

1. MVP publicável (US2+US1) → release 0.1.0 candidata
2. US3 → memória converge entre clientes (valor do `uvx` real)
3. US4 → onboarding PT-BR + validação de carteira (adoção sem suporte)
4. Polish → gates + pipeline de release → **publicar 0.1.0 no PyPI**

### Notas de execução

- T003 (ajuste de imports) deve manter a suíte verde a cada passo — nunca commitar quebrado
- T010 e T017 dividem `bootstrap.py`; T013/T022 dividem `wallet_client.py`; T023/T018 dividem `server.py` — ordem importa com executor único
- A sonda live do probe (D4) já foi feita manualmente em 18/10/2026; T021 a fixa como regressão
- Publicação no PyPI (final do release workflow) é ato manual do mantenedor com credenciais próprias (Assumptions da spec)
