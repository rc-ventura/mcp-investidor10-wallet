---
description: "Task list for spec 004 - Hardening"
---

# Tasks: Hardening — robustez, privacidade e confiança antes da distribuição Desktop

**Input**: Design documents from `/specs/004-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (`error-envelope.md`, `privacy-mode.md`, `memory-concurrency.md`, `ops-and-docs.md`), quickstart.md

**Tests**: OBRIGATÓRIOS — a Constituição exige TDD (escrever, ver falhar,
implementar, ver passar; correção de bug começa por teste que a reproduz).
Em cada fase os testes vêm antes da implementação e a implementação NUNCA é
paralela ao teste correspondente.

**Organization**: tasks agrupadas por user story. A US6 (execução semanal dos
testes `live`) saiu desta spec e foi para o roadmap, então não há fase para
ela; a numeração das demais USs foi mantida. **As fases seguem a ordem de
dependência do plan, não a numeração das USs** (cada US continua
independentemente testável): US7 → US1 → US4 → US5 → US3 → US8 → US2.
Termo padronizado: **"modo privacidade"** (`WALLET_MASK_VALUES`),
**"changelog da memória"** (`memory.json.log`).

**Execução**: SEQUENCIAL em lotes com branch própria e gate de aprovação do
mantenedor entre lotes (mesma convenção da spec 003) — ver "Fatiamento" no
fim. Marcas `[P]` descrevem apenas o desenho lógico.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: [US1]…[US8] conforme spec.md
- Caminhos exatos de arquivo em cada task
- Regras globais de código (Constituição, Formato e Estilo): sem docstring de
  módulo, sem emojis, comentários de no máximo uma linha e só quando
  indispensável, nenhuma menção a ADR/FR/SC/spec dentro do código ou
  comentários, `TODO` como único marcador de revisão; mensagens de operador
  em PT-BR e mensagens ao modelo em inglês (ADR-0009)

## Path Conventions

Pacote: `src/investidor10_wallet/` · Testes: `tests/unit/`, `tests/contract/`,
`tests/integration/`, `tests/fixtures/` · Docs: `docs/`, `docs/adrs/`,
`docs/learning-lessons/` · CI: `.github/workflows/`

---

## Phase 1: Setup (dependência, CI, higiene) — Lote 1

**Purpose**: preparar dependência, matriz de CI com Windows e arquivos
ignorados antes de tocar o código.

- [x] T001 Adicionar `filelock==4.2.4` a `dependencies` em `pyproject.toml` (pin exato, publicada em 2026-10-19, >=7 dias; `requires_python >=3.11`, sem dependências próprias) e regenerar o lock com `uv lock`; conferir `uv sync --locked` e que `uv tree --package filelock` mostra a dependência direta de `mcp-investidor10-wallet`
- [x] T002 [P] Adicionar `windows-latest` à matriz `os` de `.github/workflows/ci.yml` (hoje `ubuntu-latest`, `macos-latest`; manter `fail-fast: false`, Python 3.11/3.12/3.13 e os passos `uv run pytest`, `ruff check`, `ruff format --check`)
- [x] T003 [P] Garantir em `.gitignore` as entradas `memory.json.log`, `memory.json.lock` e `*.broken-*` (adicionar só as que faltarem; `memory.json` já deve estar)
- [x] T004 Registrar o baseline antes de alterar código: `uv run pytest` verde (anotar o total de testes no corpo do PR do lote) e `uv run ruff check . && uv run ruff format --check .` limpos

**Checkpoint**: dependência travada, matriz com Windows definida, baseline verde.

---

## Phase 2: Foundational (suíte existente compatível com Windows) — Lote 1

**Purpose**: a matriz com Windows só é útil se a suíte existente não quebrar
por motivos alheios à feature. BLOQUEIA a validação de todas as histórias.

- [x] T005 [P] Marcar com `@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: <motivo>")` os testes existentes que dependem de POSIX, localizados com `grep -rn "os.chmod\|symlink\|/bin/sh\|stat.S_\|fake_bin_dir" tests/`: testes do assistente de instalação que usam `fake_bin_dir` (`#!/bin/sh`) em `tests/unit/test_installer_cli.py`, `tests/unit/test_installer_clients.py`, `tests/unit/test_installer_dispatch.py`, e asserts de modo 0700/0600 ou de symlink em `tests/unit/test_bootstrap.py` e `tests/unit/test_memory_store.py`; testes de memória, trava e changelog NÃO ganham skip (rodam nas 3 plataformas)

**Checkpoint (gate do Lote 1)**: suíte existente verde em macOS, Linux e Windows na CI.

---

## Phase 3: User Story 7 — Inicialização sem inspecionar o diretório corrente (Priority: P3) — Lote 2

**Goal**: `resolve_memory_path` reduzida a override verbatim ou local canônico;
o diretório corrente nunca é lido (FR-029…FR-031).

**Independent Test**: iniciar a resolução num cwd com um `memory.json` solto:
o arquivo não é lido, copiado, renomeado nem alterado e o retorno é o
canônico (SC-008).

### Tests for User Story 7 (escrever primeiro; o teste do cwd DEVE falhar antes da T007)

- [x] T006 [US7] Reescrever `tests/unit/test_bootstrap.py` na parte de memória: remover todos os testes de migração/conflito/legado (os que exercitam `_atomic_copy`, `MIGRATED_MESSAGE`, `CONFLICT_RESOLVED_MESSAGE`, `MIGRATION_FAILED_MESSAGE`, `memory.json.legacy-*`, parâmetros `cwd`/`now`); adicionar: (a) `WALLET_MEMORY_PATH` definido é devolvido verbatim e nada mais é inspecionado nem criado; (b) sem override, `<home>/.investidor10/` é criado (0700 no POSIX, teste com skip no Windows) e `<home>/.investidor10/memory.json` é devolvido; (c) `memory.json` regular no cwd com conteúdo conhecido permanece byte a byte idêntico, com o mesmo inode e sem backup criado, e o retorno é o canônico (SC-008); (d) link simbólico no lugar de `memory.json` canônico → `SystemExit` com `CANONICAL_DIR_FAILED_MESSAGE`; (e) diretório canônico que é link simbólico → `SystemExit` com a mesma mensagem

### Implementation for User Story 7

- [x] T007 [US7] Simplificar `src/investidor10_wallet/bootstrap.py`: `resolve_memory_path(home=None, environ=None)` fica "override verbatim → `_ensure_canonical_dir` + `_ensure_not_symlink` → canônico"; remover `_atomic_copy`, os ramos de conflito e migração, as constantes `MIGRATION_FAILED_MESSAGE`, `MIGRATED_MESSAGE`, `CONFLICT_RESOLVED_MESSAGE`, os parâmetros `cwd` e `now` e os imports que ficarem sem uso (`tempfile`, `datetime`); manter `CANONICAL_DIR_FAILED_MESSAGE`, `_ensure_canonical_dir` e `_ensure_not_symlink` inalterados; conferir com `grep -rn "legacy\|MIGRATED\|CONFLICT_RESOLVED\|_atomic_copy" src tests` que não restou referência
- [x] T008 [P] [US7] Emendar `docs/adrs/0010-ciclo-de-vida-do-bootstrap-e-migracao.md` com a seção "Emenda 2026-10-27 (spec 004)": condição de invalidação nº 1 antecipada (migração removida na 0.3.0, não na 1.0.0), §3–4 de hardening da migração encerrados, o bootstrap deixa de inspecionar o cwd
- [x] T009 [P] [US7] Anotar em `specs/002-distribution-readiness/contracts/packaging-and-config.md` §4 que as linhas Conflito, Migração e Falha de migração foram superadas pela spec 004 (apontar para `specs/004-hardening/contracts/memory-concurrency.md`), sem apagar o histórico

**Checkpoint**: US7 testável sozinha; `uv run pytest tests/unit/test_bootstrap.py` verde.

---

## Phase 4: User Story 1 — Memória não perde gravações com vários clientes (Priority: P1) — Lote 3

**Goal**: toda gravação serializada entre processos e partindo do disco;
leituras refletem o disco; transições de alerta uma única vez; trava
indisponível → somente leitura (FR-001…FR-006, FR-038, FR-039).

**Independent Test**: dois processos sobre a mesma memória, 100 gravações
intercaladas cada → 200 entradas com ids únicos, nas 3 plataformas (SC-001);
gravação em A visível na próxima leitura de B (SC-002).

### Tests for User Story 1 (escrever primeiro; DEVEM falhar antes da T013)

- [x] T010 [P] [US1] Criar `tests/unit/test_memory_locking.py` com `MemoryStore(path, lock_timeout=...)` (parâmetro novo, default 5.0): (a) edição externa do arquivo entre duas leituras é refletida pela segunda (FR-003); (b) arquivo corrompido → `available=False`; consertado por fora → próxima operação volta a `available=True` sem reinício; (c) lock segurado por outro `filelock.FileLock(f"{path}.lock")` com `lock_timeout=0.2` → escrita levanta `MemoryBusyError` e o arquivo fica intacto (sem gravação parcial); (d) `filelock` levantando `OSError(errno.ENOSYS)` na sonda → `store.read_only is True`, leituras funcionam, escrita levanta `MemoryReadOnlyError`, e a mensagem PT-BR `LOCK_UNSUPPORTED_MESSAGE` vai a stderr (capsys); (e) dois `MemoryStore` sobre o mesmo arquivo corrompido geram um único `*.broken-*` (mesmo conteúdo → nome com o mesmo `<sha8>`; conteúdo corrompido diferente → segundo backup); (f) `os.replace` falhando com `PermissionError` 3 vezes e depois funcionando → gravação conclui (monkeypatch de `os.replace` e `time.sleep`; tentativas esperadas 50, 100, 200 ms); falhando 5 vezes → `MemoryUnavailableError`; (g) `next_id`: duas instâncias alternando `add` geram ids distintos
- [x] T011 [P] [US1] Criar `tests/integration/memory_worker.py` (função de topo `run(path, label, count)` que abre `MemoryStore(path)` e faz `count` chamadas `save_rule(f"{label}-{i}")`) e `tests/integration/test_memory_concurrency.py` usando `multiprocessing.get_context("spawn")`: (a) 2 processos × 100 gravações → 200 regras, ids únicos, todas as etiquetas presentes (SC-001); (b) regra gravada no processo A aparece no `get_rules` de um `MemoryStore` já aberto no processo B, sem reiniciar (SC-002); roda nas 3 plataformas, sem skip
- [x] T012 [P] [US1] Acrescentar a `tests/unit/test_alerts.py`: (a) dois `MemoryStore` sobre o mesmo arquivo avaliam o mesmo alerta atingido em sequência → a primeira devolve o alerta em `triggered`, a segunda devolve lista vazia e o arquivo tem uma única transição `triggered` (US1 cenário 3); (b) `get_session_context` com o store em `read_only` devolve `memory_status == "read_only"`, `triggered_alerts == []` e o digest da memória, e não grava; (c) `get_session_context` com `MemoryBusyError` devolve o envelope de erro `memory_busy` (não `memory_status: "unavailable"`); (d) `memory_busy`/`memory_read_only` saem de `memory_error_payload` com o `code` correspondente

### Implementation for User Story 1

- [x] T013 [US1] Em `src/investidor10_wallet/memory_store.py` e `src/investidor10_wallet/bootstrap.py`: criar `MemoryBusyError` e `MemoryReadOnlyError` como subclasses de `MemoryUnavailableError`, cada classe com atributo `code` (`"memory_unavailable"` na base, `"memory_busy"`, `"memory_read_only"`); criar em `bootstrap.py` a constante PT-BR `LOCK_UNSUPPORTED_MESSAGE` com o texto exato de `contracts/memory-concurrency.md` ("A memória em {path} está em um sistema de arquivos sem suporte a trava (ex.: pasta de rede). Leituras seguem funcionando, mas gravações serão recusadas para não perder dados. Aponte WALLET_MEMORY_PATH para um disco local (ex.: ~/.investidor10/memory.json) e reinicie."); mensagens das exceções em inglês no estilo recurso + causa + próxima ação (textos-alvo em `contracts/error-envelope.md`)
- [x] T014 [US1] Em `memory_store.py`: `MemoryStore.__init__(self, path, lock_timeout=5.0)` cria `filelock.FileLock(f"{path}.lock", timeout=lock_timeout, fallback_to_soft=False, thread_local=False)`; adicionar o context manager `_locked()` com contador de profundidade: adquire a trava (`filelock.Timeout` → `MemoryBusyError`) e faz o reload do disco (`_load()`) SOMENTE na aquisição mais externa (profundidade 0→1), para que seções aninhadas não descartem mutações em andamento; sonda de trava no `__init__` (adquirir/liberar) e `OSError` com `errno.ENOSYS` → `self.read_only = True` + `bootstrap.warn(LOCK_UNSUPPORTED_MESSAGE.format(path=...))`; em `read_only`, leituras fazem reload sem trava e escritas levantam `MemoryReadOnlyError`; `_load()` passa a reavaliar `available` a cada reload (arquivo consertado volta a `available=True`); arquivo ausente continua criando o store vazio v1
- [x] T015 [US1] Em `memory_store.py`: envolver em `with self._locked():` TODA operação pública — leituras (`get_all`, `find`, `get_wallet_goal`, `get_theses`, `get_rules`, `list_price_alerts`, `session_digest`) e escritas (`add`, `update`, `set_wallet_goal`, `log_decision`, `record_decision_outcome`, `log_insight`, `create_price_alert`, `cancel_price_alert`, `evaluate_alerts`); `next_id` e a escrita calculados dentro da mesma seção crítica; `log_insight` faz a checagem de fingerprint e o `add` na MESMA seção (uma só aquisição externa); `evaluate_alerts` só dispara alertas ainda `active` depois do reload; `save()` passa a ser chamado com a trava já mantida pelo chamador (não adquire por conta própria); nenhuma I/O de rede dentro da seção crítica
- [x] T016 [US1] Em `memory_store.py`: gravação atômica com retry — `PermissionError` em `os.replace` é retentado até 5 vezes com espera 50, 100, 200, 400 e 800 ms (`time.sleep`), ainda dentro da trava; esgotadas → `MemoryUnavailableError` como hoje; backup de arquivo corrompido passa a se chamar `f"{self.path}.broken-{stamp}-{sha256(content)[:8]}"` e é pulado quando já existe `{self.path}.broken-*-{sha8}` com o mesmo hash; manter 0o600 no backup
- [x] T017 [US1] Em `src/investidor10_wallet/server.py`: `memory_error_payload` usa `exc.code` (mensagem = `str(exc)`); `_memory_or_param_error` continua distinguindo `MemoryUnavailableError` (qualquer subclasse) de `ValueError`; reescrever `get_session_context` em três fases — (1) `memory.session_digest()` e a lista de alertas `active` (cada chamada reabre seção crítica própria), (2) busca de cotações sem trava, (3) `memory.evaluate_alerts(quotes)`; com `memory.read_only` pular a fase 3 e devolver `memory_status: "read_only"`; `MemoryBusyError` devolve `memory_error_payload(exc)`; atualizar a docstring da tool (inglês, sem citar decisões) listando `memory_status` = `ok` | `unavailable` | `read_only`
- [x] T018 [US1] Ajustar os testes existentes que assumiam estado em memória sem reload — os que editam `store.data` direto ou chamam `store.save()` sem a trava, localizados em `tests/unit/test_memory_store.py`, `tests/unit/test_alerts.py` e `tests/contract/test_tools_schemas.py` — para gravar pela API do store ou editar o arquivo em disco; a suíte inteira volta a verde
- [x] T019 [P] [US1] Criar `docs/adrs/0013-concorrencia-da-memoria-multiprocesso.md` (formato dos ADRs existentes, via skill `adr`, que também atualiza o índice do `CLAUDE.md`): trava `filelock` fail-closed (`fallback_to_soft=False`), arquivo `.lock` separado, reload sob trava no nível mais externo, bootstrap em 3 fases, modo somente-leitura, backup com hash, suporte Windows e retry do `os.replace`, alternativas rejeitadas (`portalocker`, stdlib `fcntl`/`msvcrt`, trava por `mtime`, SQLite), referência à emenda 1.2.0 da Constituição; acrescentar emenda curta ao §4 de `docs/adrs/0001-platform-and-storage-choices.md` registrando `filelock` como a única dependência de runtime adicional
- [x] T020 [P] [US1] Criar a learning lesson `docs/learning-lessons/filelock_fallback_soft_silencioso.md` (skill `learning-lesson`, que atualiza o `CLAUDE.md`): por padrão `filelock.FileLock` troca para `SoftFileLock` em silêncio quando o sistema de arquivos devolve `ENOSYS` no `flock`; a trava soft sobrevive a crash e bloquearia todos os processos; `fallback_to_soft=False` faz a falha propagar; fonte: `filelock/_unix.py` e `_api.py` (4.2.2) e a docstring do parâmetro
- [x] T021 [US1] Validar o quickstart V1 e V2 em máquina real: dois clientes (ex.: Claude Code em dois terminais) sobre o mesmo `WALLET_MEMORY_PATH`, salvar regra em um e listar no outro; simular FS sem trava e conferir a mensagem PT-BR e o erro `memory_read_only`; Windows validado pela CI (T002)

**Checkpoint (gate do Lote 3)**: V1/V2 do quickstart validados; suíte verde nas 3 plataformas, incluindo a concorrência com `spawn`.

---

## Phase 5: User Story 4 — Histórico auditável da memória (Priority: P2) — Lote 4

**Goal**: exatamente um registro append-only por mutação, escrito sob a trava
antes do `save()`, best-effort (FR-016…FR-020).

**Independent Test**: sequência de gravações (regra, tese, resultado de
decisão, objetivo, alerta disparado) → um registro por mudança, com estado
anterior e novo, e o valor anterior de qualquer entrada recuperável (SC-004).

### Tests for User Story 4 (escrever primeiro; DEVEM falhar antes da T023)

- [x] T022 [P] [US4] Criar `tests/unit/test_memory_changelog.py` (arquivo em `<path>.log`, uma linha JSON por mutação com as chaves `ts`, `pid`, `op`, `collection`, `id`, `before`, `after`): (a) `save_rule`/`save_thesis`/`log_decision`/`create_price_alert` → `op == "create"` e `before is None`; (b) `store.update("theses", id, {...})`, `record_decision_outcome` e `cancel_price_alert` → `op == "update"` com `before` e `after` corretos (cópias profundas: mudar `after` depois não altera a linha); (c) `set_wallet_goal` → `op == "set"`, `collection == "wallet_goal"`, `id is None`, `before is None` no primeiro `set` e o objetivo anterior no segundo; (d) `evaluate_alerts` com 2 alertas atingidos → 2 linhas `op == "trigger"`; (e) `log_insight` deduplicado → nenhuma linha nova; (f) `op` é um de `create | update | set | trigger` e `collection` um de `theses | rules | decisions | insights_log | alerts | wallet_goal`; (g) `pid == os.getpid()`; (h) `<path>.log` existindo como DIRETÓRIO (escrita impossível) → a gravação na memória acontece normalmente e stderr recebe `CHANGELOG_FAILED_MESSAGE`; (i) `os.replace` falhando → `MemoryUnavailableError` mas a linha da tentativa está no log; (j) no POSIX o arquivo é criado 0600 (skip no Windows); (k) duas sequências de mutações em 2 processos geram linhas íntegras (cada linha parseável) e o total é igual ao número de mutações

### Implementation for User Story 4

- [x] T023 [US4] Em `memory_store.py` e `bootstrap.py`: criar `bootstrap.CHANGELOG_FAILED_MESSAGE` = "Aviso: não foi possível registrar a mudança em {path} ({cause}); a gravação na memória seguiu normalmente."; implementar `_append_changelog(op, collection, entry_id, before, after)` (linha `json.dumps(..., ensure_ascii=False, allow_nan=False)` + `\n`, `ts` = `now_iso()`, `pid` = `os.getpid()`, arquivo `f"{self.path}.log"` aberto com `os.open(..., O_WRONLY | O_CREAT | O_APPEND, 0o600)`; qualquer `OSError`/`ValueError` → `bootstrap.warn(...)` e segue); chamar sempre dentro da seção crítica e ANTES de `save()` em `add()` (`create`, `before=None`), `update()` (`update`), `set_wallet_goal()` (`set`, `entry_id=None`) e `evaluate_alerts()` (`trigger`, uma chamada por alerta); `before`/`after` como `copy.deepcopy`, capturando `before` antes de `entry.update(...)`/`alert.update(...)` mutar o dict; sem mudança de schema nem de contrato de nenhuma tool
- [x] T024 [US4] Validar o quickstart V3: sequência real de gravações via agente e `cat "$WALLET_MEMORY_PATH.log" | jq -c '{op, collection, id}'` com uma linha por mutação; log sem permissão de escrita não derruba a tool

**Checkpoint (gate do Lote 4)**: V3 validado; testes de changelog verdes nas 3 plataformas.

---

## Phase 6: User Story 5 — Erros sinalizados como erro (Priority: P2) — Lote 5

**Goal**: todo erro previsto sai com `isError=true` + envelope + código e
mensagem no texto; respostas de sucesso inalteradas; mensagens no estilo
recurso + causa + próxima ação (FR-021…FR-025, FR-036).

**Independent Test**: provocar cada código do conjunto fechado e conferir
`is_error`, `structured_content["error"]["code"]` e o código em `content[0].text`
(SC-005).

### Tests for User Story 5 (escrever primeiro; DEVEM falhar antes da T027)

- [x] T025 [P] [US5] Criar `tests/contract/test_error_signal.py` com `Client(mcp).call_tool(..., raise_on_error=False)` e um caso parametrizado por código, cada um afirmando `result.is_error is True`, `result.structured_content["error"]["code"] == <código>` e o código mais o início da mensagem em `result.content[0].text`: `source_unavailable` (respx devolvendo 500 sem cache), `unexpected_format` (respx devolvendo `{}` em `get_wallet_summary`), `invalid_asset_type` (`get_wallet_positions` com `"Foo"`), `ticker_not_found` (respx 404), `asset_type_not_supported` (respx 410), `invalid_params` por DUAS vias (argumento de tipo errado no schema → `ValidationError` do framework; e `get_patrimony_history(months=0)` → erro de domínio), `memory_unavailable` (arquivo corrompido), `not_found` (`cancel_price_alert(999)`), `memory_busy` (store do servidor trocado por `MemoryStore(path, lock_timeout=0.1)` com a trava segurada por outro `FileLock`), `memory_read_only` (store com sonda forçada a `ENOSYS`); mais: sucesso de `get_wallet_summary` com `is_error is False` e `structured_content` idêntico ao snapshot atual (FR-024); mensagens de `not_found` citam `list_price_alerts` (alerta) e `get_session_context` (decisão); `asset_type_not_supported` cita `get_wallet_positions`; todas as mensagens são inglês e nomeiam recurso + causa + próxima ação (asserção por tool nomeada onde o contrato lista uma)
- [x] T026 [US5] Atualizar os testes existentes que leem payload de erro via `Client.call_tool` para passar `raise_on_error=False` (o client passa a levantar `ToolError` por padrão quando `isError` vem verdadeiro): `tests/contract/test_tools_schemas.py` e `tests/integration/test_live_api.py` (os asserts atuais continuam como estão); conferir que ficam verdes ANTES e DEPOIS da T027

### Implementation for User Story 5

- [x] T027 [US5] Em `src/investidor10_wallet/server.py`: renomear `ParameterErrorMiddleware` para `ErrorSignalMiddleware`; em `on_call_tool`, o `ValidationError` devolve `ToolResult(structured_content={"error": {"code": "invalid_params", ...}}, is_error=True)`; para o retorno normal de `call_next`, se `result.structured_content` é dict e tem a chave de topo `error`, devolver `ToolResult(content=result.content, structured_content=result.structured_content, is_error=True)`; qualquer outro resultado e qualquer outra exceção passam intactos (exceção inesperada continua no canal do framework); atualizar o `mcp.add_middleware(...)`
- [x] T028 [US5] Revisar as mensagens de erro previstas para o estilo recurso + causa + próxima ação, nomeando tool do servidor quando houver (tabela de `contracts/error-envelope.md`), em `src/investidor10_wallet/wallet_client.py` (`SourceError`), `src/investidor10_wallet/server.py` (`_not_found`, mensagem do middleware, que passa a nomear a tool e o parâmetro inválido quando disponível) e `src/investidor10_wallet/memory_store.py` (exceções); preservar as substrings que os testes existentes já afirmam; o teste da T025 passa a verde
- [x] T029 [P] [US5] Criar `docs/adrs/0014-sinal-duplo-de-erro.md` (skill `adr`): `isError` + envelope por middleware único, conjunto fechado de 11 códigos (3 novos; 12 após a emenda de 28/10/2026, que acrescentou `state_conflict`), decisão de NÃO adicionar `retryable`/`category` (função do código, tabela no contrato), exceções inesperadas fora do conjunto, fundamentos (fastmcp 4.0.11 `tools/base.py`, docs gofastmcp.com `/clients/tools`, SEP-1303/2145); emendar `docs/adrs/0007-passthrough-envelope-and-structured-errors.md` com o conjunto de 11 códigos; acrescentar a `docs/research/tool-error-channels.md` a nota de que o ponto "Não marca `isError`" foi resolvido pela spec 004

**Checkpoint (gate do Lote 5)**: 11 dos 12 códigos cobertos (o 12º, `privacy_mode_unavailable`, entra na US3); sucesso inalterado; suíte verde.

---

## Phase 7: User Story 3 — Modo privacidade (Priority: P2) — Lote 6

**Goal**: com `WALLET_MASK_VALUES` ligado, nenhuma resposta de tool de carteira
contém montante em R$ nem quantidade; só campos reconhecidos passam; tools
monetárias ficam indisponíveis (FR-009…FR-015, FR-013 com `get_earnings`).

**Independent Test**: modo ligado, todas as tools de carteira contra
fixtures com todos os campos do payload real → nenhum campo/valor monetário na
saída serializada, `privacy.omitted` correto, percentuais intactos (SC-003).

### Tests for User Story 3 (escrever primeiro; DEVEM falhar antes da T034)

- [x] T030 [P] [US3] Criar fixtures anonimizadas em `tests/fixtures/privacy/` — `summary.json` (chaves `type, applied, equity, variation, profit_twr, profit_amount, profit_twr_12m, profit_twr_12m_amount, currency`), `allocation.json` (lista de itens com `value, name, type, percent`) e `positions_<Ticker|Fii|EtfInternational|Treasure|Crypto>.json` (topo `total, weighted, draw` + uma linha com TODAS as chaves da classe conforme o probe de `research.md` D8) — valores sintéticos, com os campos monetários usando números sentinela distintivos (ex.: `987654.32`) que os testes procuram na saída serializada
- [x] T031 [P] [US3] Acrescentar a `tests/unit/test_bootstrap.py` os testes de `load_config`: `WALLET_MASK_VALUES` ∈ `1`, `true`, `yes`, `on` (case-insensitive, espaços aparados) → `mask_values is True`; ∈ `0`, `false`, `no`, `off` ou ausente → `False`; qualquer outro (`talvez`, vazio com espaços) → `SystemExit` com exatamente "WALLET_MASK_VALUES={value!r} inválido: use 1/true/yes/on para ligar ou 0/false/no/off para desligar. Corrija o ambiente e reinicie o servidor."
- [x] T032 [P] [US3] Criar `tests/unit/test_privacy.py`: `privacy.mask(tool, envelope)` para as 3 tools mascaráveis com as fixtures da T030 — mantém exatamente as allowlists A (summary), B (cada item da alocação), C (topo de posições) e D (cada linha) de `contracts/privacy-mode.md`; campo desconhecido injetado na fixture some da saída e aparece em `privacy.omitted`; `omitted` ordenado e sem repetição; envelope ganha `"privacy": {"masked": true, "omitted": [...]}`; `cached`/`fetched_at` preservados; com o modo desligado a função devolve o envelope idêntico e SEM a chave `privacy`; o envelope original (cache) não é mutado
- [x] T033 [P] [US3] Criar `tests/contract/test_privacy_mode.py` e acrescentar o 11º código ao `tests/contract/test_error_signal.py`: com o modo ligado, `get_wallet_summary`, `get_wallet_allocation` e `get_wallet_positions` nas 5 classes (respx servindo as fixtures) não contêm nenhuma chave omitida e nenhum valor sentinela na saída serializada (`json.dumps(result.structured_content)` e `content[0].text`) (SC-003); `get_patrimony_history` e `get_earnings` → `privacy_mode_unavailable` com `is_error`, SEM nenhuma requisição HTTP (`respx` com `assert_all_called` falso e contagem de chamadas zero); `get_earnings` com datas invertidas continua `invalid_params`; `get_asset_quote`, tools de memória e `get_session_context` inalteradas; modo desligado → respostas iguais às de hoje; cada docstring das 3 tools mascaráveis contém "privacy.masked" e as duas indisponíveis citam "privacy_mode_unavailable"; nenhuma tool ganha parâmetro de privacidade (comparar `inputSchema` das tools com e sem o modo); alternar o modo entre dois processos nunca serve dado cru de cache em resposta mascarada

### Implementation for User Story 3

- [x] T034 [US3] Em `src/investidor10_wallet/bootstrap.py`: `load_config` lê `WALLET_MASK_VALUES` (valores aceitos e comparação da T031) e devolve `mask_values: bool`; constante `INVALID_MASK_MESSAGE` com o texto exato da T031; constante `MASK_ACTIVE_MESSAGE` = "Modo privacidade ativo: montantes em reais e quantidades não serão enviados ao modelo."
- [x] T035 [US3] Criar `src/investidor10_wallet/privacy.py` (módulo novo, coeso: config + allowlists + máscara; sem docstring de módulo): `configure(config)`, `enabled()`, constantes `SUMMARY_FIELDS`, `ALLOCATION_FIELDS`, `POSITIONS_TOP_FIELDS`, `POSITION_ROW_FIELDS` com as listas A–D de `contracts/privacy-mode.md` e `mask(tool, envelope)` que devolve NOVO envelope (cópia) filtrado por allowlist (fail-closed: campo fora da lista é omitido, inclusive objetos aninhados), com `privacy.masked` e `privacy.omitted` (nomes removidos nesta resposta, ordenados, sem repetição); modo desligado devolve o envelope como veio
- [x] T036 [US3] Em `src/investidor10_wallet/wallet_client.py`: extrair de `WalletClient.get_earnings` o método público `resolve_earnings_period(start_date, end_date)` (padrão dos últimos 12 meses, validação de formato e inversão, levantando `SourceError("invalid_params", ...)` como hoje) e usá-lo em `get_earnings`, sem mudar comportamento nem mensagens; necessário para validar datas sem buscar a fonte quando o modo privacidade está ligado
- [x] T037 [US3] Em `src/investidor10_wallet/server.py`: aplicar `privacy.mask(...)` na saída de `get_wallet_summary`, `get_wallet_allocation` e `get_wallet_positions` (depois do cache, nunca antes); com `privacy.enabled()`, `get_patrimony_history` devolve o erro `privacy_mode_unavailable` sem chamar a fonte e `get_earnings` chama antes `wallet_client.wallet_client.resolve_earnings_period(...)` (para `invalid_params` seguir igual) e então devolve o mesmo erro; mensagens em inglês no estilo do contrato ("get_earnings is unavailable: the operator enabled privacy mode, which withholds monetary amounts. Use get_wallet_allocation or get_wallet_positions for percentage-based analysis; do not estimate the withheld amounts."); acrescentar às docstrings das 3 tools mascaráveis a frase "When the envelope has `privacy.masked` true, the operator withheld monetary amounts and quantities: work with the percentages and ratios provided and never estimate or reconstruct the withheld values." e às 2 indisponíveis a menção a `privacy_mode_unavailable`; em `main()` chamar `privacy.configure(config)` e, se ligado, `bootstrap.warn(MASK_ACTIVE_MESSAGE)`
- [x] T038 [P] [US3] Em `plugin/skills/resumo-de-dividendos/SKILL.md`: instruir o tratamento de `privacy_mode_unavailable` em `get_earnings` (informar que o modo privacidade está ligado e que o resumo de proventos em R$ não está disponível; usar apenas indicadores de DY por ativo de `get_wallet_positions`; nunca estimar); acrescentar a `tests/contract/test_plugin_assets.py` a asserção de que o SKILL cita `privacy_mode_unavailable` e que o conteúdo continua idêntico entre os clientes (invariante existente)
- [x] T039 [P] [US3] Criar `docs/adrs/0015-modo-privacidade-wallet-mask-values.md` (skill `adr`): env var e nunca parâmetro de tool (o modelo não pode desligar), allowlist fail-closed, aplicação depois do cache, marcador `privacy`, `get_patrimony_history` e `get_earnings` indisponíveis sem razão derivada, campos de semântica incerta (`weighted`, `gnr`, `gnp`, `ranking`) omitidos até haver evidência, texto livre da memória não mascarado, limite: o ID da carteira segue sendo a credencial
- [x] T040 [US3] Validar o quickstart V5 com a carteira real: `WALLET_MASK_VALUES=1`, pedir "como está minha carteira e onde devo aportar?" e conferir análise por percentuais sem nenhum R$ ou quantidade, explicação do agente sobre os montantes omitidos e indisponibilidade de `get_earnings`/`get_patrimony_history`; `WALLET_MASK_VALUES=talvez` aborta com a mensagem PT-BR

**Checkpoint (gate do Lote 6)**: V5 validado; as 12 linhas do contrato de erro cobertas; suíte verde.

---

## Phase 8: User Story 8 — Descoberta e regra de validação (Priority: P3) — Lote 7

**Goal**: `instructions=` com propósito + índice (sem comportamento do agente)
e ADR da regra de validação para as tools novas (FR-032…FR-034).

**Independent Test**: listar os metadados do servidor e ver a descrição geral;
ADR registrado com escopo explícito.

### Tests for User Story 8 (escrever primeiro; DEVEM falhar antes da T042)

- [x] T041 [P] [US8] Criar `tests/contract/test_instructions.py`: `mcp.instructions` não vazio, com no máximo 600 caracteres, contendo `get_session_context`, `privacy.masked`, `isError` e "15 minutes"; sem nenhuma das palavras `Portuguese`, `persona`, `you are`, `always respond` (case-insensitive); cada regra de uso existente continua nas docstrings das tools (asserção das frases `cached`/`fetched_at` e `~15 minutes` já presentes) — nenhuma invariante depende de `instructions`

### Implementation for User Story 8

- [x] T042 [US8] Em `src/investidor10_wallet/server.py`: constante `INSTRUCTIONS` (inglês) com o conteúdo-alvo de `contracts/ops-and-docs.md` ("Read-only access to one public Investidor10 wallet plus a persistent investor memory (theses, rules, decisions, price alerts). Start every session with get_session_context. Wallet tools return a data envelope {cached, fetched_at, data}; errors return {error: {code, message}} with isError set. B3 quotes carry ~15 minutes of delay. When privacy.masked is true, the operator withheld monetary amounts.") e `FastMCP("investidor10-wallet", instructions=INSTRUCTIONS)`
- [x] T043 [P] [US8] Criar `docs/adrs/0016-validacao-de-payloads-em-tools-novas.md` (skill `adr`): um `BaseModel` pydantic por endpoint NOVO, usado só em `model_validate` (validate-then-passthrough: o envelope devolve o payload cru), `Strict` para bool-vs-int, `FiniteFloat` para NaN/inf, falha → `unexpected_format`; explícito: sem retrofit das tools existentes (4 ciclos verdes) e sem pydantic no schema do `memory.json` (semântica de degradação continua custom); pydantic segue transitiva do FastMCP, e se deixar de ser a regra exige emenda da Constituição V.1

**Checkpoint (gate do Lote 7a)**: `instructions` visível no cliente; ADR-0016 publicado.

---

## Phase 9: User Story 2 — Documento de privacidade (Priority: P1) — Lote 7

**Goal**: o investidor entende, em PT-BR, o que vai para onde antes de adotar
(FR-007, FR-008). Fica por último porque descreve comportamento já implementado
(modo privacidade, trava, changelog).

**Independent Test**: um leitor novo responde, só com `docs/PRIVACY.md`, às
quatro perguntas do SC-007.

### Tests for User Story 2 (escrever primeiro; DEVEM falhar antes da T045)

- [x] T044 [P] [US2] Criar `tests/contract/test_privacy_doc.py` e acrescentar a `tests/unit/test_installer_cli.py`: `docs/PRIVACY.md` existe e tem as 6 seções do contrato (o que vai para onde; a credencial é o link; modo privacidade; privacidade total; memória em pasta sincronizada; telemetria), cita `WALLET_MASK_VALUES`, `memory.json.log`, `memory.json.lock` e a frase de que o botão de mascarar do site é só visual; sem emojis; o `README.md` linka `docs/PRIVACY.md` e documenta a limitação de pasta sincronizada (mesma máquina segura, duas máquinas simultâneas não protegidas); a saída final do assistente de instalação contém a linha de privacidade com a URL absoluta de `docs/PRIVACY.md` no GitHub

### Implementation for User Story 2

- [x] T045 [US2] Escrever `docs/PRIVACY.md` (PT-BR, sem jargão) com as 6 seções de `contracts/ops-and-docs.md`: tabela "o que vai para onde" (Investidor10 · provedor do modelo · arquivo local); o ID/link da carteira é a credencial e o botão de mascarar é cosmético (verificado em 17/10/2026); modo privacidade — como ligar, o que preserva (alocação, rebalanceamento por %, fundamentos, DY por ativo) e o que perde (valores em R$, histórico de patrimônio, proventos em R$), com a nota de que texto livre da memória não é mascarado; privacidade total exige modelo local (sem promessa de suporte); memória em pasta sincronizada (Dropbox/iCloud/OneDrive) segura na mesma máquina e sem proteção entre máquinas simultâneas; o produto não envia telemetria
- [x] T046 [P] [US2] Em `README.md`: link para `docs/PRIVACY.md` no topo, `WALLET_MASK_VALUES` na tabela de variáveis de ambiente, nota sobre a trava, os arquivos `.lock`/`.log` ao lado da memória e a limitação de pasta sincronizada; remover qualquer menção à migração de `./memory.json` e à memória "no diretório do repositório"
- [x] T047 [P] [US2] Em `src/investidor10_wallet/installer/cli.py`: acrescentar ao relatório final a linha PT-BR "Privacidade: veja https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/PRIVACY.md" (constante em módulo, sem alterar o fluxo de registro nem o exit code)
- [ ] T048 [US2] Validar o SC-007 com um leitor que não conhece o projeto: ler só `docs/PRIVACY.md` e responder o que vai ao Investidor10, o que vai ao provedor do modelo, o que fica local e por que o link da carteira é a credencial; ajustar o texto até as 4 respostas saírem corretas (pendente: exige um leitor humano que não conheça o projeto)

**Checkpoint (gate do Lote 7)**: documento aprovado pelo mantenedor; link no README e no instalador.

---

## Phase 10: Polish & Cross-Cutting — Lote 8

**Purpose**: versão, changelog, índices e validação final.

- [x] T049 Atualizar a versão para `0.3.0` em `src/investidor10_wallet/__init__.py` (fonte do `hatch`) e ajustar `tests/contract/test_packaging_contract.py` se ele fixar a versão anterior
- [x] T050 [P] Em `CHANGELOG.md` adicionar a seção `0.3.0` (FR-037): trava da memória multi-processo e suporte a Windows; `memory.json.log`; erros com `isError` e 3 códigos novos (`memory_busy`, `memory_read_only`, `privacy_mode_unavailable`); modo privacidade `WALLET_MASK_VALUES`; `instructions` do servidor; `docs/PRIVACY.md`; **remoção da migração `./memory.json`** com a instrução "quem ainda tem memória no diretório do repositório: `mv ./memory.json ~/.investidor10/memory.json` ou defina `WALLET_MEMORY_PATH`"
- [x] T051 [P] Conferir que o `CLAUDE.md` lista os ADRs 0013–0016 e a nova learning lesson (os skills `adr` e `learning-lesson` devem tê-los inserido nas tasks T019, T020, T029, T039, T043); corrigir à mão o que faltar, incluindo a data
- [x] T052 [P] Atualizar `docs/ROADMAP.md`: marcar `[x]` os itens atendidos pela 004 na Fase 1 (file lock, changelog da memória, sinal duplo de erro, doc de privacidade, modo privacidade, `instructions=`, CHANGELOG, validação via pydantic como decisão de design, remoção da migração legada) e registrar na sequência que a 004 foi entregue; os itens Ollama e action semanal de live tests permanecem abertos
- [x] T053 Varredura de estilo da Constituição nos arquivos tocados: sem docstring de módulo, sem emojis, sem comentário de mais de uma linha, sem menção a ADR/FR/SC/spec em código ou docstrings de tools (`grep -rnE "ADR-|FR-[0-9]|SC-[0-9]|spec 00" src/`), `TODO` como único marcador de revisão
- [ ] T054 Validação final: `uv run pytest` e `uv run ruff check . && uv run ruff format --check .` verdes; CI verde em macOS, Linux e Windows; percorrer o quickstart V0–V7 e anotar o resultado no PR (feito localmente em macOS: suíte, ruff, live e V0-V7; pendente: CI nas 3 plataformas, que só roda após o push)
- [ ] T055 Rodar a revisão SDD (`/sdd-final-review`: QA + Segurança + Tech Leader) antes do merge; achados CRITICAL/HIGH resolvidos no artefato, nunca diluindo princípio da Constituição (pendente: skill disparada pelo mantenedor)

**Checkpoint (gate do Lote 8)**: gates verdes + PR final aprovado.

---

## Fatiamento em lotes (execução sequencial com gate de aprovação)

Mesma convenção da spec 003: cada lote é uma branch própria, aberta,
revisada e aprovada antes do lote seguinte começar. A emenda da Constituição
1.2.0 e o `docs/ROADMAP.md` já editados nesta branch entram no PR do Lote 1.

| Lote | Branch | Tasks | Gate de aprovação |
|---|---|---|---|
| L1 — Setup + Fundação | `spec-004/setup-windows` | T001–T005 | Suíte existente verde nas 3 plataformas na CI |
| L2 — US7 Sem migração | `spec-004/us7-sem-migracao` | T006–T009 | `test_bootstrap.py` verde; cwd intocado (SC-008) |
| L3 — US1 Trava | `spec-004/us1-trava` | T010–T021 | V1/V2 validados em máquina real; concorrência com `spawn` verde nas 3 plataformas |
| L4 — US4 Changelog | `spec-004/us4-changelog` | T022–T024 | V3 validado (uma linha por mutação) |
| L5 — US5 Sinal de erro | `spec-004/us5-sinal-erro` | T025–T029 | 12 códigos com `isError` (11 na entrega do L5, mais `state_conflict` da emenda de 28/10/2026); sucesso inalterado |
| L6 — US3 Privacidade | `spec-004/us3-privacidade` | T030–T040 | V5 validado com a carteira real; 12 códigos cobertos |
| L7 — US8 + US2 | `spec-004/us8-us2-docs` | T041–T048 | `instructions` visível; leitor novo passa no SC-007 |
| L8 — Polish 0.3.0 | `spec-004/polish-0.3.0` | T049–T055 | Gates verdes + PR final com review SDD |

---

## Dependencies

### Phase Dependencies

- **Setup (T001–T004)**: sem dependências.
- **Foundational (T005)**: depende do Setup (T002). BLOQUEIA a validação de todas as histórias em Windows.
- **US7 (T006–T009)**: depende do Foundational; independente das demais — vai primeiro porque simplifica o bootstrap.
- **US1 (T010–T021)**: depende do Foundational (e da T001 para o import de `filelock`). É o núcleo: US4 e US5 dependem dela.
- **US4 (T022–T024)**: depende da US1 (o changelog roda sob a trava, nos mesmos funis).
- **US5 (T025–T029)**: depende da US1 (`memory_busy`/`memory_read_only` usam `exc.code`). Antes da US3 para o 11º código nascer já com `isError`.
- **US3 (T030–T040)**: depende da US5 (`privacy_mode_unavailable` sai com `isError`) e da US1 (config no `load_config` convive com o bootstrap já simplificado).
- **US8 (T041–T043)**: depende da US3 (a `instructions` cita `privacy.masked`).
- **US2 (T044–T048)**: depende de US1, US3 e US4 (descreve trava, modo privacidade e changelog já implementados).
- **Polish (T049–T055)**: depende de todas as histórias desejadas.

### Within Each User Story

- Testes primeiro e FAIL antes da implementação (T006, T010–T012, T022, T025, T030–T033, T041, T044).
- Exceções e mensagens antes da trava (T013 → T014); trava antes das operações (T014 → T015 → T016); store antes do servidor (T016 → T017).
- Reload só na aquisição mais externa (T014) é pré-requisito de qualquer operação composta (T015).
- ADRs e learning lessons após o comportamento estar implementado e testado.
- Validação manual real ao final de cada história (T021, T024, T040, T048).

### Parallel Opportunities (desenho lógico, bloqueadas pela decisão sequencial)

- Setup: T002 ∥ T003; Foundational: T005 sozinha.
- US7: T008 ∥ T009 (docs).
- US1: T010 ∥ T011 ∥ T012 (arquivos de teste distintos); T019 ∥ T020 (docs).
- US5: T025 em paralelo com a preparação da T026.
- US3: T030 ∥ T031 ∥ T032 ∥ T033 (testes); T038 ∥ T039.
- US8/US2: T041 ∥ T044; T046 ∥ T047.
- Polish: T050 ∥ T051 ∥ T052.

---

## Implementation Strategy

### MVP (US1)

1. Lote 1 (Setup + Fundação) → Lote 2 (US7, rápido, reduz superfície).
2. Lote 3 (US1): é o MVP — elimina a perda silenciosa de dado e é o
   pré-requisito que motivou a spec (o Desktop da spec 005 multiplica os processos).
3. **PARAR e VALIDAR**: V1/V2 em máquina real; só então seguir.

### Entrega incremental

- Lote 4 (changelog) e Lote 5 (sinal de erro) são independentes entre si
  depois do Lote 3; a ordem do plan põe o changelog antes por compartilhar o
  funil de persistência.
- Lote 6 (privacidade) só depois do Lote 5.
- Lote 7 (docs) fecha descrevendo o que já existe; Lote 8 publica a 0.3.0.
- Cada lote deixa `main` utilizável: nenhum lote introduz contrato
  incompleto (os 3 códigos novos entram junto das tools que os emitem).
