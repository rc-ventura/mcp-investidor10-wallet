# Quickstart — validação da spec 004

Pré-requisitos: repo com `uv sync --locked`. Comandos a partir da raiz do repo. Contratos em `contracts/`.

## V0 — Suíte

```bash
uv run pytest                 # não-live, verde (SC-009)
uv run ruff check . && uv run ruff format --check .
```

Esperado: verde em macOS, Linux e Windows na CI (matriz com
`windows-latest`).

## V1 — Dois processos, nenhuma gravação perdida (US1, SC-001/002)

```bash
export WALLET_MEMORY_PATH="$(mktemp -d)/memory.json"
uv run pytest tests/integration/test_memory_concurrency.py -v
```

Esperado: 2 processos × 100 gravações → 200 entradas com ids únicos; regra
gravada no processo A aparece na leitura do processo B; alerta disparado
uma única vez com duas sessões concorrentes.

Manual: abrir dois clientes (ex.: Claude Code em dois terminais) com o
mesmo `WALLET_MEMORY_PATH`; salvar uma regra em um, pedir `get_rules` no
outro → a regra aparece sem reiniciar.

## V2 — Trava indisponível → somente leitura (FR-039)

Teste unitário com a sonda forçada a `OSError(ENOSYS)`:
gravação → `memory_read_only` com `isError`; leitura funciona;
stderr com a mensagem PT-BR do contrato.

## V3 — Changelog (US4, SC-004)

Sequência `save_rule` → `save_thesis` → `record_decision_outcome` →
`set_wallet_goal` → bootstrap com alerta atingido:

```bash
cat "$WALLET_MEMORY_PATH.log" | jq -c '{op, collection, id}'
```

Esperado: exatamente 1 linha por mutação, `before`/`after` corretos.
Com o `.log` sem permissão de escrita: a gravação na memória acontece e há
aviso em stderr.

## V4 — Sinal duplo de erro (US5, SC-005)

```bash
uv run pytest tests/contract/test_error_signal.py -v
```

Esperado: cada um dos 11 códigos com `is_error=True` e o código visível
em `content[0].text`; respostas de sucesso idênticas ao snapshot.

## V5 — Modo privacidade (US3, SC-003)

```bash
WALLET_MASK_VALUES=1 uv run pytest tests/contract/test_privacy_mode.py -v
WALLET_MASK_VALUES=talvez uv run mcp-investidor10-wallet   # exit 1, mensagem PT-BR
```

Manual (sua carteira): com `WALLET_MASK_VALUES=1`, pedir ao agente
"como está minha carteira e onde devo aportar?". Esperado: análise por
percentuais, sem nenhum R$ ou quantidade; o agente explica que os
montantes foram omitidos; `get_earnings`/`get_patrimony_history` informam
indisponibilidade.

## V6 — Sem migração legada (US7, SC-008)

```bash
cd "$(mktemp -d)" && echo '{"stray": true}' > memory.json
env -u WALLET_MEMORY_PATH WALLET_ID=<id> HOME="$(mktemp -d)" uv --directory <repo> run python -c \
  "from investidor10_wallet import bootstrap; print(bootstrap.resolve_memory_path())"
cat memory.json   # inalterado
```

Esperado: imprime `<HOME>/.investidor10/memory.json`; o `memory.json` do
cwd não foi tocado.

## V7 — Descoberta e docs (US2, US8)

- `uv run python -c "from investidor10_wallet.server import mcp; print(mcp.instructions)"`
  → propósito + índice, sem persona.
- `docs/PRIVACY.md` com as 6 seções do contrato; link no README e na
  saída do `install`.
- Leitor novo responde às 4 perguntas do SC-007 só com o documento.
- ADRs 0013–0016 e emenda do ADR-0010 presentes e indexados no `CLAUDE.md`.
