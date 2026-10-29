# Quickstart: validação end-to-end (spec 003)

Cenários que provam a feature funcionando de ponta a ponta. Pré-requisito de
todos: branch `003-client-integration`, `uv sync` rodado, suíte `uv run
pytest` verde.

## V1 — Publicação (FR-001)

1. Criar o projeto `mcp-investidor10-wallet` no PyPI; configurar trusted
   publishing: owner `rc-ventura`, repo `mcp-investidor10-wallet`, workflow
   `release.yml`, environment `pypi`.
2. No GitHub: Settings → Environments → criar `pypi` (com required reviewer).
3. `git tag v0.1.0 && git push origin v0.1.0`; acompanhar o workflow verde.
4. **Esperado**: `uvx mcp-investidor10-wallet` (fora do repo) baixa do PyPI e
   aborta com a mensagem PT-BR de `WALLET_ID` ausente.

(Concluído em 2026-10-24 — release 0.1.0 publicada com proveniência OIDC.)

## V2 — Assistente detecta e instala o bundle nos 4 CLIs (US1, FR-002…005, FR-010)

1. `uv run mcp-investidor10-wallet install --dry-run`
   → relatório SIMULAÇÃO lista os clientes presentes; "registraria o
   servidor" + "instalaria o plugin" por cliente; nada executado.
2. `uv run mcp-investidor10-wallet install`
   → pergunta o ID; valida; registra o servidor E instala o plugin em cada
   CLI presente (bundle = produto completo); relatório final pede reinício
   dos clientes.
3. `uv run mcp-investidor10-wallet install --mcp-only`
   → registra apenas o servidor, zero comando de plugin (modo técnico).
4. Executar o mesmo comando de novo → todos os status são "já registrado"
   (ou o protocolo de colisão pergunta pular/atualizar); nenhuma entrada
   duplicada (SC-003).
5. **Esperado**: `claude mcp list`, `devin mcp list`, `codex mcp list` e
   `gemini mcp list` mostram `carteira`; cada cliente reiniciado expõe as 19
   tools e o plugin carregado (skills, guardião, persona, hook).

## V3 — Plugin nos quatro clientes (US2, FR-006…009)

Pré-requisito: o servidor `carteira` já registrado via assistente (V2) — o
plugin não registra MCP.

1. Claude Code: `claude plugin marketplace add <repo>` (local durante dev:
   apontar para a pasta do repo) seguido de `/plugin install
   investidor10-carteira`.
2. Devin CLI: `devin plugins install ./plugin -y --local`.
3. Codex CLI: `codex plugin marketplace add <repo>` + instalar pela TUI
   `/plugins`.
4. Gemini CLI: `gemini extensions install <repo-url|path>`.

**Esperado**: as 3 skills (`analise-da-carteira`, `check-de-tese`,
`resumo-de-dividendos`), o subagente `guardiao-de-disciplina` (read-only), a
persona injetada no início da sessão (hook SessionStart) e o hook `Stop`
emitindo o lembrete de registro apenas propondo (nunca gravando) quando
aplicável. No Gemini, as 3 skills + os custom commands `/analise-da-carteira`,
`/check-de-tese`, `/resumo-de-dividendos`.

## V4 — Degradações (edge cases)

- Sem nenhum cliente: assistente de instalação sai 1 com orientação PT-BR.
- ID inválido/privada: sai 3 antes de qualquer registro; nenhuma configuração
  alterada.
- Cliente já tem `carteira` de outra origem: pergunta interativa sempre
  exibida — pular (default, `skipped_present`) ou atualizar (`updated`) —
  mesmo com `--yes` (protocolo de colisão do contract install-cli.md).
- Runner `uv` ausente: sai 2 com instrução PT-BR de instalação.
## Evidências (preenchidas em 2026-10-27, `main` após o merge do PR #6)

| Cenário | Resultado | Evidência |
|---|---|---|
| V1 | ✅ | Release 0.1.0 (2026-10-24) e 0.2.0 (2026-10-27, tag `v0.2.0`, run 40599673366) publicadas no PyPI com proveniência OIDC |
| V2.1 `install --dry-run` | ✅ | `uvx --refresh mcp-investidor10-wallet@0.2.0 install --dry-run`, fora do repo, baixando do PyPI: SIMULAÇÃO lista Claude Code, Devin CLI e Codex (registraria o servidor + instalaria o plugin); Gemini ausente da máquina; nada alterado |
| V2.3 `--dry-run --mcp-only` | ✅ | Só "registraria o servidor", zero linha de plugin |
| V2.2/V2.4 `install` real e reexecução | ⏳ pendente | Não executado na máquina do mantenedor (servidor `carteira` já registrado em Claude Code e Codex); será testado em outra máquina. Idempotência coberta por testes (SC-003) |
| V3 Claude Code | ✅ | `claude plugin list`: `investidor10-carteira@investidor10` enabled, escopo user |
| V3 Devin CLI | ✅ | `devin plugins list`: `investidor10-carteira` instalado |
| V3 Codex | ⏳ pendente | Instalação via TUI `/plugins` ainda não registrada |
| V3 Gemini | ⏳ pendente | CLI não instalado; formato validado só por contrato |
| V4 ID inválido | ✅ | `--wallet-id abc` → mensagem PT-BR, exit 3, nada registrado |
| V4 `--clients` inválido | ✅ | `--clients foo` → "Clientes inválidos…", exit 2 |
| V4 sem cliente / `uv` ausente / colisão | ✅ (testes) | Suíte `-k "install or plugin or hook or collision or degrad"`: 56 passed |

Pendências aceitas para o fechamento da spec: V2 real em máquina limpa,
Codex via TUI e Gemini. Não bloqueiam a 0.2.0.
