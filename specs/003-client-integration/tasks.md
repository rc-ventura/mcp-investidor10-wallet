---
description: "Task list for feature implementation"
---

# Tasks: Integração automática com clientes de agente (CLIs)

**Input**: Design documents from `/specs/003-client-integration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: OBRIGATÓRIOS nesta feature — a constituição do projeto exige TDD
(teste que falha antes, constituição estilo §4). Toda fase começa pelas tasks
de teste e a implementação correspondente NUNCA é paralela ao teste.

**Organization**: tasks agrupadas por user story (US1=assistente de
instalação para 4 CLIs, US2=plugin). Termo padronizado: **"assistente de
instalação"**. Mapeamento com o plan.md: Bloco A=publicação (Phase 1/T001),
Bloco B=US1 (Phase 3), Bloco C=US2 (Phase 4). Desktop (Claude Desktop,
extensão `.mcpb`, apps desktop) está FORA desta feature — spec futura
dedicada (decisão 2026-10-24).

**Execução**: SEQUENCIAL em lotes com branch própria e gate de aprovação do
mantenedor entre lotes (decisão 2026-10-24) — ver "Fatiamento" no fim. Marcas
`[P]` descrevem apenas o desenho lógico; nenhum lote corre em paralelo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: [US1]/[US2] conforme spec.md
- Caminhos exatos de arquivo em cada task
- Regras globais de código: sem docstring de módulo, sem emojis, comentários
  de no máximo uma linha e só quando indispensável (constituição estilo §1,
  §5, §6, §7); mensagens de operador em PT-BR (ADR-0009)

## Path Conventions

Pacote: `src/investidor10_wallet/` · Testes: `tests/unit/`, `tests/contract/`
· Plugin: `plugin/`, `.claude-plugin/`, `.devin-plugin/` (raiz, fora do
wheel)

---

## Phase 1: Setup (Publicação + estrutura) — Lote 0 + início do Lote 1

**Purpose**: completar a publicação (operação, desbloqueia validação
end-to-end) e criar a estrutura do módulo novo.

- [x] T001 Completar a publicação no PyPI (FR-001, quickstart V1 — operação, sem código): criar o projeto `mcp-investidor10-wallet` em https://pypi.org/manage/projects/; em Publishing → adicionar trusted publisher OIDC com owner `rc-ventura`, repo `mcp-investidor10-wallet`, workflow `release.yml`, environment name `pypi`; no GitHub criar o environment `pypi` (Settings → Environments, com required reviewer); rodar `git tag v0.1.0 && git push origin v0.1.0`; verificar workflow verde e `uvx mcp-investidor10-wallet` abortando com a mensagem PT-BR de `WALLET_ID` ausente baixado do PyPI
- [x] T002 [P] Criar o módulo `src/investidor10_wallet/installer/` com esqueletos vazios: `__init__.py`, `cli.py`, `clients.py` (apenas arquivos, sem implementação)
- [x] T003 [P] Adicionar fixture compartilhada em `tests/conftest.py`: `fake_bin_dir` — cria executáveis falsos (`claude`, `devin`, `codex`, `gemini`, `uv`) num diretório temporário e os coloca na PATH via `monkeypatch.setenv("PATH", ...)`, registrando as chamadas recebidas para asserções

**Checkpoint**: PyPI online (V1 verde) e pacote de testes preparado.

---

## Phase 2: Foundational (Dispatch + tipos) — continuação do Lote 1

**Purpose**: blocos que toda história usa — dispatch do subcomando no entry
point e os tipos do data-model.

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase fechar.

- [x] T004 Escrever teste (vermelho) `tests/unit/test_installer_dispatch.py`: `main()` de `server.py` com `argv[1] == "install"` despacha para `investidor10_wallet.installer.cli.run` recebendo `argv[2:]` **sem** inicializar o FastMCP; com qualquer outro argv o comportamento atual permanece
- [x] T005 Implementar o dispatch em `src/investidor10_wallet/server.py` (`main()`): `if len(sys.argv) > 1 and sys.argv[1] == "install": raise SystemExit(installer.cli.run(sys.argv[2:]))` antes de qualquer bootstrap do servidor; teste de T004 verde
- [x] T008 [P] Definir os tipos do data-model em `src/investidor10_wallet/installer/__init__.py` como dataclasses: `ClientRegistration` (name fixo `"carteira"`, command, args, env com `WALLET_ID`), `RegisterOutcome` (status no conjunto fechado `"registered" | "updated" | "skipped_present" | "skipped_absent" | "failed"`, message PT-BR), `InstallerSession` (wallet_id, outcomes, requested) — verbatim do `data-model.md`

**Checkpoint**: Fundação verde — US1/US2 podem começar.

---

## Phase 3: User Story 1 - Assistente conecta os 4 CLIs com um comando (Priority: P1) — Lote 2

**Goal**: `mcp-investidor10-wallet install` detecta clientes presentes
(**Claude Code, Devin CLI, Codex, Gemini CLI**), valida o `WALLET_ID` e
registra o servidor `carteira` em cada um via comando nativo de gestão de MCP
— idempotente, PT-BR, com o protocolo de colisão interativo (US1,
FR-002…FR-005, contract install-cli.md).

**Independent Test**: quickstart V2/V4 em máquina real com ao menos um
cliente; suíte unitária verde com binários falsos na PATH.

### Tests for User Story 1 (escrever PRIMEIRO, ver falhar)

- [ ] T009 [P] [US1] Escrever teste (vermelho) `tests/unit/test_installer_clients.py` — adapters CLI com a fixture `fake_bin_dir`: (a) detecção retorna falso e status `skipped_absent` quando o binário não existe; (b) Claude Code invoca `claude mcp add carteira --scope user -- env WALLET_ID=<id> uvx mcp-investidor10-wallet` (verbatim do contract install-cli.md); (c) Gemini invoca `gemini mcp add -s user -e WALLET_ID=<id> carteira uvx mcp-investidor10-wallet` (scope user, alias sem underscores); (d) Codex invoca `codex mcp add carteira --env WALLET_ID=<id> -- uvx mcp-investidor10-wallet` (verbatim do contract); (e) Devin invoca `devin mcp add carteira -- env WALLET_ID=<id> uvx mcp-investidor10-wallet` — baseline fixo = comando documentado no README (a existência/uso de flag de user scope do Devin NÃO é aceitação de teste; é verificação pós-impl em T014); (f) alias já registrado (`mcp list` contém `carteira`) → pergunta de colisão disparada; resposta "pular" → `skipped_present` sem reexecutar `add`; resposta "atualizar" → `updated` com reexecução do `add`
- [ ] T011 [P] [US1] Escrever teste (vermelho) `tests/unit/test_installer_cli.py` com a superfície completa do contract install-cli.md: flags `--clients`, `--wallet-id`, `--plugin`, `--dry-run`, `--yes`; códigos de saída: 0 sucesso, 1 nenhum cliente detectado, 2 runner ausente, 3 carteira inválida/privada, 4 falha em todos os registros; `--dry-run` escreve o prefixo `"SIMULAÇÃO (nenhuma configuração foi alterada)"` e não executa nenhum comando de registro; `--yes` NÃO suprime a pergunta de colisão (protocolo do contrato); `--plugin` imprime as instruções de marketplace do contract; validação do ID via `wallet_client` mockada com respx (válida vs. privada vs. 404); mensagens PT-BR com próximo passo

### Implementation for User Story 1

- [ ] T012 [US1] Implementar `src/investidor10_wallet/installer/clients.py` (após T009 falhar): `ClientAdapter` por cliente (claude/devin/codex/gemini) com `detect()` (via `shutil.which`), `list_existing()` (via `<cli> mcp list`), `register(reg: ClientRegistration) -> RegisterOutcome` + prompt de colisão interativo; comandos exatamente como o contrato; falha de subprocesso → `failed` com stderr resumido em PT-BR; teste T009 verde
- [ ] T013 [US1] Implementar `src/investidor10_wallet/installer/cli.py` (`run(argv)`): parse argparse das flags do contrato; ordem de pré-condições (runner na PATH → obter e validar `WALLET_ID` via `wallet_client` antes de qualquer registro — FR-004); orquestração dos adapters detectados/filtrados; relatório final PT-BR com uma linha por cliente (status, aviso de reinício do cliente); modo `--plugin` imprime as instruções oficiais de instalação do plugin (opt-in, FR-010); teste T011 verde
- [ ] T014 [US1] Validar em ambiente real (Devin): `uv run mcp-investidor10-wallet install --dry-run` e depois sem `--dry-run` numa máquina com `devin` presente; confirmar `devin mcp list` exibe `carteira`; rodar duas vezes e confirmar idempotência (SC-003); verificar com `devin mcp add --help` se existe flag de user scope — se divergir do baseline do README, registrar em `docs/learning-lessons/` e ajustar o contrato install-cli.md

**Checkpoint**: US1 completa e testável sozinha (MVP).

---

## Phase 4: User Story 2 - Plugin de comportamento (Priority: P2) — Lote 3

**Goal**: um conjunto de assets em `plugin/` + três manifestos finos servem
Claude Code e Devin CLI com prompts, guardião de disciplina e hook `Stop` que
propõe — nunca grava — registro na memória (US2, FR-006…FR-008, FR-009,
contract plugin-manifest.md).

**Independent Test**: quickstart V3 — instalar o plugin em cada CLI pelo
canal marketplace (Claude) e pela instalação de repo/pasta (Devin).

### Tests for User Story 2 (escrever PRIMEIRO, ver falhar)

- [ ] T015 [P] [US2] Escrever teste (vermelho) `tests/contract/test_plugin_assets.py` cobrindo as 5 invariantes do contract plugin-manifest.md: (1) os três manifestos (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.devin-plugin/plugin.json`) são JSON válidos, `name`/`version` idênticos nos do plugin e nome do marketplace coincide; (2) todos os caminhos declarados existem no repo (components e `source` do marketplace); (3) `plugin/.mcp.json` define exatamente o servidor `carteira` com `command: "uvx"`, `args: ["mcp-investidor10-wallet"]`, `env` com a referência literal `"${WALLET_ID}"` e nenhum literal numérico; (4) nenhum asset em `plugin/` menciona escrita direta a `memory.json` e `plugin/hooks/stop-memory-reminder.sh` contém a palavra de confirmação (FR-008); (5) nenhum asset contém emoji

### Implementation for User Story 2

- [ ] T016 [US2] Criar os 3 prompts em `plugin/commands/` (após T015 falhar): `analise-da-carteira.md`, `check-de-tese.md`, `resumo-de-dividendos.md` — cada um exigindo chamada de `get_session_context` antes das tools de dados e menção ao delay de cotação (verbatim do contract)
- [ ] T017 [US2] Criar `plugin/agents/guardiao-de-disciplina.md`: subagente read-only — lê `get_rules`/`get_theses` + dados, confronta a decisão, reporta violações e pede confirmação humana para `log_decision` (proibido chamar tools de escrita — verbatim FR-008)
- [ ] T018 [US2] Criar `plugin/hooks/hooks.json` (evento `Stop` apontando para o script via `"${CLAUDE_PLUGIN_ROOT}"`) + `plugin/hooks/stop-memory-reminder.sh`: lê o transcript do stdin (formato do hook `Stop`; referência local do padrão: `~/.config/devin/plugins/ralph-loop/hooks/stop-hook.sh`); se o transcript contém discussão de decisão e **não** contém chamada `log_decision`/`log_insight`, emite o lembrete pedindo confirmação do usuário; em qualquer erro ou transcript ausente → exit 0 em silêncio (fail-open — verbatim do contract)
- [ ] T019 [US2] Criar `plugin/.mcp.json` exatamente como o contract (servidor `carteira`, `env` com `"${WALLET_ID}"`)
- [ ] T020 [US2] Criar os 3 manifestos: `.claude-plugin/plugin.json` (name `investidor10-carteira`, version `0.1.0`, paths explícitos), `.claude-plugin/marketplace.json` (name `investidor10`, entry do plugin com `source: "./"` — verificar os campos suportados na doc oficial do Claude Code; divergências viram learning lesson) e `.devin-plugin/plugin.json` (mesmo name/version/description) — testes de T015 verdes
- [ ] T021 [US2] Validar manualmente (quickstart V3): no Claude Code, `claude plugin marketplace add rc-ventura/mcp-investidor10-wallet` + `/plugin install investidor10-carteira` (local durante dev); no Devin CLI, instalar da pasta e confirmar prompts/subagente/hook; se o Devin não honrar os paths do manifesto Claude, registrar divergência em `docs/learning-lessons/` e ajustar o manifesto Devin (risco documentado em research.md D2)

**Checkpoint**: US2 completa — os dois CLIs carregam os mesmos assets de um
único repo.

---

## Phase 5: Polish & Cross-Cutting Concerns — Lote 4

**Purpose**: documentação, versionamento, ADR e fechamento da feature.

- [ ] T022 [P] Atualizar `README.md`: nova seção "Instalação automática (recomendada)" com `uvx mcp-investidor10-wallet install` como caminho principal; instruções manuais rebaixadas para "Configuração manual" (incluir Codex); seção do plugin com o comando de marketplace; CORRIGIR os 4 links relativos quebrados na página do PyPI (detectado 2026-10-24 em 0.1.0): `docs/ROADMAP.md`, `specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md`, `docs/learning-lessons/get_asset_quote_apenas_acoes_b3.md`, `docs/learning-lessons/earnings_list_detalhe_proventos_por_ativo.md` → URLs absolutas `https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/...` (PyPI não resolve relativos; decisão: juntar ao 0.2.0, sem patch 0.1.1)
- [ ] T023 [P] Atualizar `CHANGELOG.md` com seção `## [0.2.0] - <data>` (Keep a Changelog PT-BR, feat→minor conforme ADR-0011) cobrindo assistente de instalação (4 CLIs) e plugin; bump de versão para `0.2.0` em `src/investidor10_wallet/__init__.py`
- [ ] T024 [P] Criar `docs/adrs/0012-integracao-automatica-de-clientes.md` consolidando D1–D5 de research.md (comandos nativos por CLI incl. Codex, três manifestos de plugin, adiamento do Desktop para spec futura, escopo user, execução sequencial em lotes) com as mesmas seções dos ADRs vizinhos; atualizar a tabela de ADRs em `CLAUDE.md`
- [ ] T025 [P] Rodar os gates: `uv run ruff check` + `uv run ruff format --check` + `uv run pytest` (não-live) verdes; pre-commit passa; CI matrix verde (3.11/3.12/3.13 × ubuntu/macos)
- [ ] T026 Executar o `specs/003-client-integration/quickstart.md` completo (V1–V4) e preencher evidências; criar PR cujo corpo referencia `specs/003-client-integration/spec.md` e roda a review SDD (QA + Segurança + Tech Leader)

---

## Fatiamento em lotes (execução sequencial com gate de aprovação)

Decisão do mantenedor (2026-10-24): **nenhuma implementação em paralelo**;
cada lote é uma branch própria, aberta, revisada e aprovada antes do lote
seguinte começar. As marcas `[P]` das tasks descrevem só o desenho lógico.

| Lote | Branch | Tasks | Gate de aprovação |
|---|---|---|---|
| L0 — Publicação | `spec-003/publicar-0.1.0` | T001 | Workflow de release verde + `uvx` baixando do PyPI (CONCLUÍDO 2026-10-24) |
| L1 — Setup + Fundação | `spec-003/setup-fundacao` | T002–T005, T008 | Suíte verde com teste T004 vermelho→verde |
| L2 — US1 Assistente | `spec-003/us1-assistente` | T009, T011–T014 | V2/V4 do quickstart validados em máquina real |
| L3 — US2 Plugin | `spec-003/us2-plugin` | T015–T021 | V3 validado (marketplace no Claude Code + Devin) |
| L4 — Polish 0.2.0 | `spec-003/polish-0.2.0` | T022–T026 | Gates verdes + PR final com review SDD |

---

## Dependencies

### Phase Dependencies

- **L0 (T001)**: sem dependências; operação externa que desbloqueia a
  validação V2-real (não bloqueia código — mocks cobrem testes).
- **L1 (T002–T005, T008)**: depende do L0 conceitualmente (não tecnicamente);
  BLOQUEIA todas as user stories.
- **L2 (US1)**: depende de L1. MVP da feature.
- **L3 (US2)**: depende de L1 (fixtures + dispatch de subcomando).
- **L4 (Polish)**: depende dos lotes desejados completados.

### Within Each User Story

- Testes primeiro e FAIL antes da implementação (T009, T011, T015).
- Tipos antes de adapters (L1 antes de L2).
- Invariantes de plugin testadas por contrato antes dos assets (T015 antes
  de T016–T020).
- Validação manual real ao final de cada história (T014, T021).

### Parallel Opportunities (desenho lógico, bloqueadas pela decisão sequencial)

- Setup: T002 ∥ T003.
- US1: T009 ∥ T011 (arquivos de teste distintos).
- US2: T016 ∥ T017 ∥ T018 ∥ T019 (sequenciais a T015).
- Polish: T022 ∥ T023 ∥ T024 ∥ T025.

---

## Notes

- [P] = arquivos diferentes, sem dependência de tasks incompletas — desenho
  lógico apenas; execução é sequencial por lote (decisão 2026-10-24).
- Labels [US1]/[US2] mapeiam para spec.md e aparecem só nas fases de
  história.
- Verificar testes falhando antes de implementar cada fase (TDD,
  constituição estilo §4).
- Commit por task ou grupo lógico; pre-commit roda ruff lint + format.
- Divergências de formato descobertas nos clientes (campos de marketplace,
  flag de user scope do Devin) → learning lesson em `docs/learning-lessons/`
  e, se decisão, ADR — nunca só na conversa (constituição, premissas vivas).