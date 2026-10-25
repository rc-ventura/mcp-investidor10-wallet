# Implementation Plan: Integração automática com clientes de agente (CLIs)

**Branch**: `003-client-integration` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-client-integration/spec.md`

## Summary

Transformar a distribuição de "pacote publicado + configuração manual por
cliente" em "um comando conecta tudo", em três frentes independentes:

1. **Completar a publicação** (FR-001): operação sobre o pipeline existente —
   projeto no PyPI, trusted publishing OIDC, environment `pypi` no GitHub,
   push da tag `v0.1.0`. Sem mudança de código. (Concluída em 2026-10-24.)
2. **Assistente de instalação `install`** (US1/P1, FR-002…005): subcomando
   stdlib-only do próprio pacote que detecta clientes presentes (**Claude
   Code, Devin CLI, Codex, Gemini CLI**), valida o `WALLET_ID` reutilizando
   `wallet_client` e registra via **comando nativo de gestão de MCP de cada
   CLI** (`claude/devin/codex/gemini mcp add`, escopo user), sempre
   idempotente e em PT-BR.
3. **Plugin de comportamento** (US2/P2, FR-006…010): mesmo repositório,
   assets em `plugin/` (3 prompts, subagente guardião de disciplina, hook
   `Stop` que propõe registro na memória sem nunca gravar sozinho) + três
   manifestos finos (`.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `.devin-plugin/plugin.json`) sobre o
   mesmo conteúdo + `.mcp.json` com `${WALLET_ID}`.

**Fora do escopo (spec futura dedicada, decisão 2026-10-24)**: Claude
Desktop, extensão `.mcpb`, Devin Desktop e demais apps desktop — exigem
estudo próprio de distribuição (conector/extensão oficial, runtime, memória e
subagentes no app).

## Technical Context

**Language/Version**: Python ≥3.11 (pacote existente).

**Primary Dependencies**: **stdlib apenas** no assistente de instalação
(`argparse`, `json`, `pathlib`, `shutil`, `subprocess`, `platform`).
Validação da carteira reusa o `wallet_client` existente (`httpx` já é runtime
pinado). Zero dependências runtime novas.

**Storage**: assistente de instalação é stateless; o estado persiste nas
configs gerenciadas pelos comandos nativos de cada cliente.

**Testing**: pytest + respx (suite existente); testes de contrato novos
parseando os manifestos e validando os assets do plugin. Executáveis nativos
(`claude`, `devin`, `codex`, `gemini`) são **mockados na PATH** nos testes.

**Target Platform**: CLIs em macOS/Linux (matriz CI atual; Windows via
comandos nativos onde existirem). Desktop fora do escopo desta feature.

**Project Type**: CLI tooling + distribuição de plugin de agente.

**Performance Goals**: assistente de instalação completo < 3 min incluindo interação (SC-001);
nenhuma escrita de arquivo > 1 s.

**Constraints**: PT-BR nas mensagens ao operador (ADR-0009); idempotência
obrigatória (FR-005); hook não grava memória sem confirmação
(FR-008, ADR-0002); hooks fail-open (limite documentado do Devin CLI);
assets do plugin não tocam `~/.investidor10/memory.json` diretamente.

**Scale/Scope**: 4 clientes CLI-alvo, ~10 FRs, 2 USs priorizadas, 1 spec.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Resultado |
|---|---|---|
| I. Documentação oficial primeiro | `research.md` cita fontes oficiais verificadas hoje para cada formato tocado: `geminicli.com/docs/tools/mcp-server` (Gemini), `learn.chatgpt.com/docs/extend/mcp` + `openai/codex` (Codex), repo oficial `anthropics/claude-code` `plugin-dev` skill (Claude), `docs/extensibility/plugins/` + `mcp/` do Devin CLI (leitura local) | PASS |
| II. Sem anti-padrões de protocolo | Assistente de instalação não toca o servidor MCP; registra apenas via comando nativo de cada CLI. Nenhum valor fabricado: falha de detecção/validação vira erro explícito PT-BR (edge cases da spec) | PASS |
| III. Uso, não comportamento | Comportamento/agente-persona vive **só** na camada plugin (harness), nunca no servidor: docstrings de tools inalteradas nesta feature | PASS |
| IV. Estado explícito, protocolo stateless | Assistente de instalação não introduz estado de sessão; plugin não cria persistência nova — memória continua só em `~/.investidor10/memory.json` | PASS |
| V. Dependências pinadas | Zero deps runtime novas (stdlib-only); assets do plugin são markdown/JSON, sem empacotamento no wheel (hatch já declara só `src/investidor10_wallet`) | PASS |
| Estilo: TDD, sem emojis, comentários mínimos | Tasks começam por testes (assistente de instalação como funções puras sobre fixtures); sem emojis nos assets do plugin; TODO só se necessário | PASS |
| ADR-0002 (memória é do usuário) | FR-008 explícita: hook propõe, usuário confirma; assistente de instalação nunca toca a memória | PASS |
| ADR-0009 (PT-BR operador) | Assistente de instalação e erros em PT-BR | PASS |
| ADR-0011 (distribuição) | Publicação usa o pipeline existente; nenhuma alteração no pipeline — a feature adiciona os passos operacionais faltantes | PASS |

**Nenhuma violação — sem justificativas necessárias.**

## Project Structure

### Documentation (this feature)

```text
specs/003-client-integration/
├── plan.md              # Este arquivo
├── research.md          # D1–D5, fontes oficiais citadas
├── data-model.md        # Entidades do assistente de instalação (sem storage novo)
├── quickstart.md        # Cenários V1–V4 de validação end-to-end
├── contracts/
│   ├── install-cli.md     # Superfície do subcomando install
│   └── plugin-manifest.md # Manifestos + marketplace + assets + .mcp.json
├── checklists/
│   └── requirements.md    # Validada 2026-10-24
└── tasks.md             # (/speckit-tasks — próxima etapa)
```

### Source Code (repository root)

```text
src/investidor10_wallet/
├── server.py               # main(): despacha argv[1] == "install" (delta mínimo)
├── wallet_client.py        # reusado pelo assistente de instalação p/ validar carteira
├── memory_store.py         # intacto
└── installer/              # NOVO — assistente de instalação (US1)
    ├── __init__.py         # dataclasses do data-model
    ├── cli.py              # parse de args, orquestração, relatório PT-BR
    └── clients.py          # adapters por CLI (claude/devin/codex/gemini)

plugin/                     # NOVO — assets de comportamento (US2), fora do wheel
├── commands/
│   ├── analise-da-carteira.md
│   ├── check-de-tese.md
│   └── resumo-de-dividendos.md
├── agents/
│   └── guardiao-de-disciplina.md
├── hooks/
│   ├── hooks.json          # evento Stop → lembrete de registro (proposição)
│   └── stop-memory-reminder.sh
└── .mcp.json               # servidor carteira com ${WALLET_ID}

.claude-plugin/plugin.json      # NOVO — manifesto Claude (paths explícitos → plugin/)
.claude-plugin/marketplace.json # NOVO — canal de instalação `plugin marketplace add`
.devin-plugin/plugin.json       # NOVO — manifesto Devin (mesmos assets)

tests/
├── unit/
│   ├── test_installer_cli.py
│   └── test_installer_clients.py
└── contract/
    └── test_plugin_assets.py
```

**Structure Decision**: layout de pacote único existente (Option 1).
`plugin/`, `.claude-plugin/` e `.devin-plugin/` ficam na raiz do repo **fora
do wheel** (o build hatchling já restringe a `src/investidor10_wallet`),
separando "motor" de "comportamento" dentro do mesmo repositório (FR-009) sem
poluir o pacote publicado.

## Complexity Tracking

> Nenhuma violação do Constitution Check — seção mantida vazia por
> conformidade.

## Sequencing (visão de entrega)

1. **Bloco A — Publicação (operação, sem código)**: PyPI trusted publishing +
   environment `pypi` + tag `v0.1.0`. Desbloqueia V1. (Concluído.)
2. **Bloco B — Assistente de instalação `install`** (US1): módulo
   `installer/` + dispatch no `main()` + testes TDD.
3. **Bloco C — Plugin** (US2): assets + 3 manifestos (2 plugin + 1
   marketplace) + `.mcp.json` + teste de contrato dos assets.

**Execução é SEQUENCIAL em lotes com gate de aprovação do mantenedor entre
cada lote** (decisão 2026-10-24): os blocos viram branches separadas — embora
B e C sejam tecnicamente independentes entre si, nenhum lote é executado em
paralelo. Bloco C depende apenas da Fundação (dispatch + fixtures).
