# Implementation Plan: Hardening — robustez, privacidade e confiança antes da distribuição Desktop

**Branch**: `004-hardening` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-hardening/spec.md`

## Summary

Endurecer o servidor antes da spec 005 (Desktop), que multiplica os
processos sobre a mesma memória e amplia a base de usuários. Sete frentes,
quase todas independentes:

1. **Memória multi-processo** (US1, P1): trava `filelock` em arquivo irmão
   (`memory.json.lock`, fail-closed com `fallback_to_soft=False`), reload do
   disco no início de toda operação, `next_id`/transições de alerta na mesma
   seção crítica, `get_session_context` em 3 fases (trava → cotações sem
   trava → trava), modo somente-leitura quando o FS não suporta trava.
   Suporte a macOS, Linux e **Windows** (retry do `os.replace`, ACL do
   perfil), com `windows-latest` na CI.
2. **Doc de privacidade** (US2, P1): `docs/PRIVACY.md` PT-BR + links.
3. **Modo privacidade** (US3): `WALLET_MASK_VALUES` → allowlist por tool
   aplicada na saída (depois do cache), marcador `privacy`, e
   `get_patrimony_history`/`get_earnings` indisponíveis.
4. **Changelog da memória** (US4): JSONL `memory.json.log` com
   `{ts, pid, op, collection, id, before, after}` nos 4 funis.
5. **Sinal duplo de erro** (US5): o middleware marca `isError=true` em todo
   resultado com `error` no topo; 3 códigos novos; mensagens revisadas.
7. **Remoção da migração legada** (US7): `resolve_memory_path` reduzida a
   override → canônico.
8. **Descoberta e regra de validação** (US8): `instructions=` + ADR-0016.

Versão alvo **0.3.0**.

## Technical Context

**Language/Version**: Python ≥3.11 (CI: 3.11, 3.12, 3.13).

**Primary Dependencies**: `fastmcp==4.0.11`, `httpx==0.28.1` e **novo**
`filelock==4.2.4` (autorizado pela emenda 1.2.0, Constituição V.1; já
estava na árvore como transitiva de dev). Sem outras dependências novas.

**Storage**: `memory.json` (schema v1 inalterado) + irmãos `.lock`,
`.log` (JSONL) e `.broken-*` — ver data-model.md.

**Testing**: pytest + pytest-asyncio + respx (existente). Novos:
concorrência real com `multiprocessing` (`spawn`), contratos de
`isError`/privacidade via `fastmcp.Client` (`raise_on_error=False`),
fixtures de payload anonimizadas a partir do probe de chaves.

**Target Platform**: servidor MCP stdio local em macOS, Linux e Windows.

**Project Type**: pacote Python (servidor MCP + CLI de instalação) + plugin
de comportamento.

**Performance Goals**: seção crítica da trava < 50 ms típica (reload + save
de arquivo de KB); nenhuma I/O de rede dentro da trava; overhead do
mascaramento desprezível.

**Constraints**: timeout de trava 5 s; mensagens operador PT-BR / modelo
inglês (ADR-0009); nenhuma mudança de schema da memória nem do contrato de
sucesso das tools; fail-closed em privacidade e em trava.

**Scale/Scope**: usuário único, 2–4 processos concorrentes, escrita em
escala humana; 36 FRs, 7 USs (US6 movida para o roadmap).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Resultado |
|---|---|---|
| I. Documentação oficial primeiro | research.md cita código instalado (`fastmcp` 4.0.11 `tools/base.py`; `filelock` 4.2.2 `_unix.py`/`_api.py`), docs gofastmcp.com (`/servers/server`, `/clients/tools`) e PyPI. Pendente na implementação: revalidar a doc oficial do `filelock` para a 4.2.4 | PASS (com 1 verificação registrada como tarefa) |
| II.1 Erros nunca como sucesso | É o objetivo da US5: `isError` + envelope em 100% dos erros previstos, incluindo `invalid_params` do middleware | PASS |
| II.2 Valores nunca fabricados | Modo privacidade omite (nunca zera/estima); tools monetárias devolvem erro; nenhuma razão derivada no servidor (FR-013) | PASS |
| II.3 Exceção inesperada é bug | Middleware só converte resultados com `error`; exceções seguem o canal do framework | PASS |
| II.4 Trigger-phrase | 3 códigos novos e as mensagens revisadas nomeiam recurso, causa e tool (contracts/error-envelope.md) | PASS |
| III. Uso, não comportamento | `instructions=` = propósito + índice, testado contra persona; regras de mascaramento nas docstrings; nenhuma invariante depende de `instructions` | PASS |
| IV. Estado explícito | Estado continua só no `memory.json`; a trava não é estado de protocolo; idempotência do disparo de alerta reforçada sob concorrência | PASS |
| V.1 Deps de runtime | `filelock` é a única adição e é exatamente a classe autorizada pela emenda 1.2.0; pin 4.2.4 (≥7 dias); ADR-0013 + ADR-0001 §4. Pydantic segue transitiva (ADR-0016) | PASS |
| V.2 Upgrade consciente | Nenhum upgrade de FastMCP | PASS |
| Estilo (TDD, sem emojis, comentários de 1 linha, sem citar ADR/FR no código, TODO) | Tasks começam por testes; contratos com mensagens literais testáveis | PASS |
| Gates: contrato de tools/canais de erro → ADR | ADR-0014 (erros), 0015 (privacidade), 0013 (memória), 0016 (validação), emenda 0010; learning lesson do `fallback_to_soft` | PASS |

**Re-check pós-design**: sem violações. O design adicionou dois pontos de
atenção (sem violação): (a) `get_session_context` em três fases para não
segurar a trava durante I/O de rede; (b) testes POSIX-only marcados para
pular no Windows com motivo explícito — cobertura das plataformas preservada
para memória/trava/changelog.

## Project Structure

### Documentation (this feature)

```text
specs/004-hardening/
├── plan.md                      # Este arquivo
├── research.md                  # D1–D14
├── data-model.md                # arquivos irmãos, changelog, estados do store
├── quickstart.md                # V0–V7
├── contracts/
│   ├── error-envelope.md        # isError + 11 códigos
│   ├── privacy-mode.md          # WALLET_MASK_VALUES + allowlists
│   ├── memory-concurrency.md    # trava, changelog, caminho, plataformas
│   └── ops-and-docs.md          # PRIVACY.md, instructions, ADR-0016, CHANGELOG
├── checklists/requirements.md
└── tasks.md                     # /speckit-tasks
```

### Source Code (repository root)

```text
src/investidor10_wallet/
├── server.py          # ErrorSignalMiddleware; instructions=; mascaramento nas 3 tools;
│                      # privacy_mode_unavailable; get_session_context em 3 fases; docstrings
├── memory_store.py    # trava + reload; read_only; changelog; backup com hash; retry do replace
├── privacy.py         # NOVO — config do modo + allowlists + mask(envelope, tool)
├── bootstrap.py       # WALLET_MASK_VALUES; resolve_memory_path simplificada (sem cwd)
├── wallet_client.py   # inalterado
└── installer/cli.py   # linha final com link para PRIVACY.md

plugin/skills/resumo-de-dividendos/SKILL.md   # tratar privacy_mode_unavailable

tests/
├── unit/test_memory_store.py            # reload, read_only, changelog, backup único
├── unit/test_bootstrap.py               # sem testes de migração; WALLET_MASK_VALUES; cwd ignorado
├── unit/test_privacy.py                 # NOVO — allowlists, fail-closed
├── integration/test_memory_concurrency.py  # NOVO — multiprocessing spawn
├── contract/test_error_signal.py        # NOVO — 11 códigos, sucesso inalterado
├── contract/test_privacy_mode.py        # NOVO — SC-003
└── contract/test_tools_schemas.py       # raise_on_error=False onde lê erro

.github/workflows/ci.yml     # + windows-latest
docs/PRIVACY.md              # NOVO
docs/adrs/0013..0016-*.md    # NOVOS; 0010 e 0001 emendados
docs/learning-lessons/filelock_fallback_soft_silencioso.md  # NOVO
CHANGELOG.md, README.md, CLAUDE.md, .gitignore, pyproject.toml, uv.lock,
src/investidor10_wallet/__init__.py (0.3.0)
specs/002-distribution-readiness/contracts/packaging-and-config.md  # §4 anotado
```

**Structure Decision**: layout existente (src layout, ADR-0011). Um único
módulo novo (`privacy.py`), justificado por coesão: config + allowlists +
função de máscara formam uma unidade testável isolada e não pertencem nem
ao transporte (`wallet_client`) nem às tools (`server`). Trava e changelog
ficam no `memory_store.py` (são o funil de persistência; separar criaria
módulos minúsculos — Constituição, "Modularização com parcimônia").

## Ordem sugerida (dependências)

1. **Fundação**: `filelock` no `pyproject.toml`/`uv.lock`; CI com Windows
   (antes de mexer na memória, para ver os testes POSIX-only quebrando).
2. **US7** (remoção da migração) — simplifica o bootstrap antes de US1.
3. **US1** (trava + reload + read_only + Windows) — maior risco, P1.
4. **US4** (changelog) — mesmo funil de US1.
5. **US5** (sinal duplo) — muda testes de contrato; antes de US3, que cria
   um código novo.
6. **US3** (modo privacidade) + skill de dividendos.
7. **US2/US8** (PRIVACY.md, instructions, ADRs, CHANGELOG, README) — fecha
   descrevendo o comportamento já implementado.

## Riscos

| Risco | Mitigação |
|---|---|
| Testes existentes assumem estado em memória do `MemoryStore` sem reload (ex.: editam `store.data` direto) | Ajustar para gravar via API ou via arquivo; o reload é a nova verdade |
| Testes POSIX-only quebram no Windows | `skipif(win32)` com motivo; memória/trava/changelog sem skip |
| `os.replace` no Windows segurado por antivírus/sincronização | retry com backoff dentro da trava; persistindo, `memory_unavailable` |
| Cliente que trata `isError` de forma agressiva (ex.: esconde o conteúdo) | o texto do content carrega o JSON completo; validado no Claude Code; Desktop na spec 005 |

## Complexity Tracking

Sem violações da Constituição a justificar.
