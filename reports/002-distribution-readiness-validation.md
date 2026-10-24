# Validação — spec 002 (Prontidão para distribuição)

Data: 2026-10-18. Executor: ciclo de implementação e fechamento pós-review do
plano `specs/002-distribution-readiness/plan.md` (tasks T001–T030 + correções
do ciclo 1 de SDD Final Review, ADR-0010).

## Resultados por cenário do quickstart

| Cenário | Resultado | Evidência |
|---|---|---|
| S1 — instalação de 1 linha sem clone | OK | Wheel instalado em venv limpo (`/tmp/smoke-venv-verify`); `mcp-investidor10-wallet` invocado via subprocess responde ao handshake JSON-RPC `initialize` no stdout com `serverInfo.name == "investidor10-wallet"` |
| S2 — memória compartilhada entre processos | OK | Regra salva por um processo lida por nova instância de `MemoryStore` apontando para o mesmo caminho canônico (`~/.investidor10/memory.json`) |
| S3 — startup sem carteira configurada | OK | Exit 1, mensagem PT-BR no stderr (`WALLET_ID não configurado` + `investidor10.com.br/carteira`), zero chamadas de rede e zero escrita no stdout (testes unitários + smoke test do wheel) |
| S4 — validação da carteira | OK | 200 segue silenciosamente; 404 → exit 1 PT-BR (confirmado em unit + live); 401/403 → exit 1 PT-BR; 5xx/429/timeout → warning PT-BR no stderr + startup continua (9 testes unitários em `test_bootstrap.py` + 2 testes live) |
| S5 — migração da memória | OK | Migração real do `./memory.json` do autor para `~/.investidor10/memory.json` verificada (dir 0700, arquivo 0600, 1 regra, 4 decisões, 2 alertas íntegros) + 10 testes unitários em `test_bootstrap.py` cobrindo `OVERRIDE`, `NOVO_CANONICO` (criação de `~/.investidor10` 0700 + primeira escrita persistida), `MIGRADO`, `CANONICO_WINS` (backup com microssegundos), guarda `cwd == ~/.investidor10`, falha de cópia, falha de `unlink` com rollback, rejeição de symlinks (`lstat`/`O_NOFOLLOW`) e verificação de inode |
| S6 — regressão de comportamento | OK | 225 testes não-live + 5 testes live verdes no novo layout; shapes das 19 tools inalterados; `import investidor10_wallet.server` sem side effects de env, rede ou disco |
| S7 — gates de qualidade | OK | `uv run ruff check .` (0 erros), `uv run ruff format --check .` (71 arquivos formatados, incluindo fences Python nos `.md` de `docs/learning-lessons/`) e `uv run pre-commit run --all-files` verdes |
| S8 — release seco | OK parcial | `uv build` gera sdist + wheel (`hatchling==1.32.4` pinado); smoke test do wheel valida import sem `WALLET_ID`, exit 1 com mensagem PT-BR e handshake `initialize` stdio; `LICENSE` (MIT) presente; `release.yml` com gate `environment: pypi` e seção `## [0.1.0]` no `CHANGELOG.md`. Publicação real no PyPI exige tag `v0.1.0` e credenciais OIDC do mantenedor |

## Contagens

- Suíte não-live (`uv run pytest`): **225 passed**
  - 192 testes pré-existentes ajustados para imports do pacote (`test_memory_store.py`, `test_wallet_client.py`, `test_alerts.py`, `test_tools_schemas.py`).
  - 28 testes unitários em `tests/unit/test_bootstrap.py`: 7 de configuração (`load_config`, incluindo rejeição de dígitos Unicode via `[0-9]+`), 10 da máquina de estados e endurecimento de migração (`resolve_memory_path`), 9 do probe (`validate_wallet`), 1 de pureza de import sem env/disco e 1 da ordem determinística do pipeline em `main()`.
  - 5 testes de contrato de empacotamento em `tests/contract/test_packaging_contract.py` (incluindo subprocess JSON-RPC `initialize` sobre stdio).
- Suíte live (`uv run pytest -m live`): **5 passed** (3 pré-existentes + 2 do probe).
- Total: **230 passed**.

## Desvios e correções registrados (pós-review ciclo 1)

1. **`main()` não chamava `mcp.run()` e side effects rodavam no import**: corrigido em `server.py` e `wallet_client.py` (ADR-0010) — toda a cadeia `load_config() -> configure() -> resolve_memory_path() -> MemoryStore() -> validate_wallet() -> mcp.run()` roda dentro de `main()`, mantendo os singletons de módulo via `_allow_unconfigured=True` e `_LazyMemory`.
2. **Fresh install (`NOVO_CANONICO`) não criava `~/.investidor10/`**: `resolve_memory_path()` agora garante a criação do diretório canônico com modo `0700` antes do `MemoryStore`, evitando degradação silenciosa na primeira escrita.
3. **Endurecimento da migração e do cliente HTTP (ADR-0010)**: adicionados `os.lstat`/`os.O_NOFOLLOW` contra symlinks, verificação de `(st_dev, st_ino)` antes de `legacy.unlink()`, rollback do canônico se `unlink` falhar, sufixo de microssegundos no backup de conflito, guarda para `cwd == ~/.investidor10`, `follow_redirects=False` e regex `[0-9]+`.
4. **Fences Python em Markdown (`docs/learning-lessons/*.md`)**: o `ruff format` (0.17.0) formata blocos Python em arquivos `.md` quando executado sobre `.`. Decisão explícita: formatar os 3 arquivos de learning lessons com `ruff format` (registrado no `CHANGELOG.md`) para manter `ruff format --check .` e `pre-commit` 100% alinhados sem exclusões.

## Pendências fora do executor

- Publicar no PyPI (tag `v0.1.0` + trusted publishing no ambiente `pypi` do GitHub) — ato do mantenedor.
- Validar primeira execução real dos workflows `ci.yml` e `release.yml` no GitHub Actions após push.
- Hardening agendado para próximo ciclo: avaliar upgrade testado `fastmcp` -> `>=4.1.0`, validação de body no probe 200 e SHA-pinning das GitHub Actions.