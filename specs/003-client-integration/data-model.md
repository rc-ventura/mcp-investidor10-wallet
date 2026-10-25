# Data Model: Integração automática com clientes de agente (spec 003)

O assistente de instalação é stateless entre execuções. Nenhuma entidade nova
é persistida pelo produto — o estado vive nas configurações gerenciadas pelos
comandos nativos de cada cliente (`claude/devin/codex/gemini mcp add`). Os
tipos abaixo são as estruturas em memória do assistente; servem de contrato
interno entre `cli.py` e `clients.py`.

## ClientRegistration (por cliente, em memória)

| Campo | Tipo | Regras |
|---|---|---|
| `name` | str | alias do servidor, fixo `"carteira"` (sem underscores — restrição Gemini) |
| `command` | str | runner de execução, sempre `"uvx"` nesta feature |
| `args` | list[str] | `["mcp-investidor10-wallet"]` |
| `env` | dict[str, str] | `{"WALLET_ID": <id validado>}` — único campo exigido |

## ClientAdapter (abstração por cliente)

| Campo | Tipo | Regras |
|---|---|---|
| `client_id` | str | `"claude"`, `"devin"`, `"codex"`, `"gemini"` |
| `detect()` | → bool | presença do binário na PATH (`shutil.which`) |
| `list_existing()` | → bool | o alias `carteira` já está registrado? (via `<cli> mcp list`) — base da idempotência |
| `register(reg: ClientRegistration)` | → `RegisterOutcome` | executa o comando nativo de `add` do contrato install-cli.md |

## RegisterOutcome (resultado por cliente)

| Campo | Tipo | Regras |
|---|---|---|
| `client_id` | str | id do cliente |
| `status` | `"registered" \| "updated" \| "skipped_present" \| "skipped_absent" \| "failed"` | conjunto fechado; `skipped_present` implementa idempotência |
| `message` | str | PT-BR, compõe o relatório final |

## InstallerSession (relatório final; não persistido)

| Campo | Tipo | Regras |
|---|---|---|
| `wallet_id` | str | validado antes de qualquer registro (FR-004); nunca logado além do relatório ao usuário |
| `outcomes` | list[RegisterOutcome] | um por cliente detectado ou explicitado em `--clients` |
| `requested` | set[str] | normalizado de `--clients` (padrão: todos os detectados) |

## Validações cruzadas

1. `WALLET_ID` inválido ou carteira privada → `InstallerSession` aborta sem
   nenhum `outcome` (FR-004; validação antes de tudo).
2. Nenhum cliente detectado e nenhum `--clients` explícito → exit 1 com
   orientação PT-BR.
3. Duas execuções → segunda produz só `skipped_present` (ou o protocolo de
   colisão decide `updated` com confirmação explícita) (SC-003).

## Transições de estado

Nenhuma: o assistente é uma função sobre o estado atual das CLIs presentes na
PATH e das entradas reportadas por seus comandos `mcp list`. Estados
terminais (`registered`, `skipped_present`) são idempotentes por construção.