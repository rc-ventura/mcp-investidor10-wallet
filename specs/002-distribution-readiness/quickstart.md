# Quickstart — Validação ponta a ponta (spec 002)

Guia de validação da feature. Referências: [contracts/packaging-and-config.md](contracts/packaging-and-config.md) (contratos citados como C1–C7), [data-model.md](data-model.md).

## Pré-requisitos

- `uv` instalado (≥ versão pinada do projeto) e Python 3.11+.
- Uma carteira **pública** do Investidor10 e seu ID (URL: `investidor10.com.br/carteira/<ID>`).
- Clone do repositório **apenas para desenvolvimento** — os cenários de usuário (S1–S2) exigem ambiente sem o repo.

## S1 — Instalação de uma linha sem clone (SC-001, C1/C2)

Ambiente limpo (sem o repositório):

```bash
uvx mcp-investidor10-wallet   # com WALLET_ID exportado
```

**Esperado**: pacote baixado do PyPI, servidor sobe em stdio, nenhum checkout de código. Tempo total desde a página do projeto até sessão funcionando no cliente do agente: < 10 minutos seguindo só o README.

## S2 — Configuração de clientes (SC-003, C1/C6)

1. Configurar Claude Desktop com caminho **absoluto** do `uv` (`which uv`) — C1 §exemplo.
2. Configurar Claude Code (`claude mcp add`) com o mesmo `uvx`.
3. Em um cliente: `save_rule("só compro com recomendação positiva")`.
4. No outro cliente: `get_rules` na sessão seguinte.

**Esperado**: a regra aparece no segundo cliente sem configuração de caminho (ambos usam `~/.investidor10/memory.json`).

## S3 — Startup sem carteira configurada (SC-002, C2/C6)

```bash
env -u WALLET_ID uvx mcp-investidor10-wallet; echo "exit=$?"
```

**Esperado**: exit 1; stderr PT-BR nomeando `WALLET_ID` e a URL pública onde achar o ID; **zero** chamadas à API (verificar por ausência de latência/log de rede); nada no stdout. Idem para `WALLET_ID=abc123` (não numérico).

## S4 — Validação da carteira (SC-004, C5/C6)

| Cenário | Comando | Esperado |
|---|---|---|
| ID inexistente | `WALLET_ID=99999999999 uvx ...` | exit 1, PT-BR "não encontrada ou não é pública" + próximos passos |
| Fonte fora (simular) | env `https_proxy` apontando para porta morta | warning no stderr + servidor **sobe**; tools de carteira retornam `source_unavailable`; memory tools funcionam |
| TOC de GUI | — | README troubleshooting resolve "MCP failed to connect" apontando o PATH absoluto sem inspeção de logs |

## S5 — Migração da memória legada (SC-005, C4)

Do diretório do repositório (onde existe `memory.json` do autor):

```bash
uvx mcp-investidor10-wallet   # 1ª execução da versão nova
```

**Esperado (MIGRADO)**: `~/.investidor10/memory.json` criado (dir 0700, arquivo 0600) com **todas** as coleções do legado (`diff` de conteúdo idêntico); `./memory.json` removido; aviso no stderr com os dois caminhos.

**Conflito (CANONICO_WINS)**: recriar `./memory.json` com conteúdo diferente e rodar de novo → canônico vence, legado renomeado para `memory.json.legacy-*`, aviso no stderr. **Override**: com `WALLET_MEMORY_PATH=/tmp/outra.json`, nenhuma migração acontece.

**Falha (permissão)**: `chmod 500 ~/.investidor10` (ou destino inexistente não criável) → exit 1 PT-BR com o caminho tentado; legado **intocado**.

## S6 — Regressão de comportamento das tools (FR-010)

```bash
uv sync --locked && uv run pytest            # suite completa (não-live) no novo layout
uv run pytest -m live                        # opt-in: inclui ID inexistente → 404
```

**Esperado**: suit de testes verde no novo layout com imports pelo pacote; nenhum shape de resposta das tools alterado (contratos da spec 001 intactos).

## S7 — Gates de qualidade (SC-006, C7)

- `pre-commit run --all-files` → ruff lint + format verdes.
- PR aberto → CI: matriz 3.11/3.12/3.13 × ubuntu/macos, `pytest` (não-live) verde.

## S8 — Release seco (SC-006, C7)

1. `uv build` → sdist + wheel.
2. Smoke test local: instalar o wheel num venv limpo, `python -c "import investidor10_wallet"` e rodar o console script sem `WALLET_ID` → exit 1 com mensagem PT-BR.
3. Dry-run do workflow: tag `v0.1.0` num fork/branch de teste → release.yml verde até o passo de publish (ou publish em TestPyPI).

**Esperado**: `CHANGELOG.md` com seção `## [0.1.0]`; gate de changelog falha a pipeline se a seção faltar; pacote publicado em `pypi.org/project/mcp-investidor10-wallet`.
