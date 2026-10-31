# Data Model — spec 004 Hardening

O schema do `memory.json` **não muda** (continua `version: 1`, FR-020).
Entram três artefatos irmãos do arquivo de memória e um estado novo do
store.

## Arquivos ao lado da memória

Todos derivam do caminho em uso (`WALLET_MEMORY_PATH` ou
`~/.investidor10/memory.json`), sempre no mesmo diretório.

| Arquivo | Papel | Criado por | Permissão (POSIX) | Git |
|---|---|---|---|---|
| `memory.json` | estado (inalterado) | `MemoryStore.save()` | 0600 | ignorado |
| `memory.json.lock` | trava entre processos; conteúdo irrelevante; nunca removido | `filelock` no primeiro acquire | 0600 | ignorado |
| `memory.json.log` | changelog append-only (JSONL) | primeira mutação | 0600 | ignorado |
| `memory.json.broken-<YYYYMMDD-HHMMSS-ffffff>-<sha8>` | backup de arquivo corrompido (nome ganha hash do conteúdo) | reload que encontra arquivo inválido | 0600 | ignorado |

No Windows, as permissões vêm da ACL do diretório (perfil do usuário); o
servidor não altera ACLs.

## Registro de mudança (linha do `memory.json.log`)

```json
{"ts": "2026-10-27T14:03:11.402-03:00", "pid": 48211, "op": "update",
 "collection": "theses", "id": 3,
 "before": {"id": 3, "ticker": "MXRF11", "text": "...", "updated_at": "..."},
 "after":  {"id": 3, "ticker": "MXRF11", "text": "...", "updated_at": "..."}}
```

| Campo | Tipo | Regra |
|---|---|---|
| `ts` | string ISO-8601 com offset | `MemoryStore.now_iso()` no momento da mutação |
| `pid` | int | `os.getpid()` do processo que gravou |
| `op` | enum `create` \| `update` \| `set` \| `trigger` | ver tabela abaixo |
| `collection` | enum `theses` \| `rules` \| `decisions` \| `insights_log` \| `alerts` \| `wallet_goal` | |
| `id` | int \| null | `null` só para `wallet_goal` |
| `before` | object \| null | cópia profunda do estado anterior; `null` em `create` e no primeiro `set` |
| `after` | object | cópia profunda do estado novo |

| Funil | `op` | Tools que passam por ele |
|---|---|---|
| `add()` | `create` | `save_thesis`, `save_rule`, `log_decision`, `log_insight` (só quando não deduplica), `create_price_alert` |
| `update()` | `update` | `record_decision_outcome`, `cancel_price_alert` |
| `set_wallet_goal()` | `set` | `set_wallet_goal` |
| `evaluate_alerts()` | `trigger` (1 linha por alerta) | `get_session_context` |

Regras:
- uma mutação gera **exatamente uma** linha (SC-004); `log_insight`
  deduplicado não gera linha (nada mudou);
- escrita sob a trava e **antes** do `save()`: uma mutação cujo save falha
  fica registrada (FR-017);
- falha ao escrever o log → aviso em stderr, a operação continua (FR-018);
- o arquivo só cresce (sem rotação nesta feature).

## Estado do `MemoryStore`

```text
            reload ok                      reload: arquivo inválido / versão > 1
  ┌──────────────────────┐        ┌──────────────────────────────────────┐
  ▼                      │        ▼                                      │
available ───────────────┴──▶ unavailable ──(reload ok: arquivo consertado)──┘
   │
   └── sonda de trava: ENOSYS ──▶ read_only (fixo pelo resto do processo)
```

| Estado | Leituras | Escritas | `get_session_context.memory_status` |
|---|---|---|---|
| `available` | reload sob trava | reload + mutação + log + save sob trava | `ok` |
| `unavailable` | `memory_unavailable` | `memory_unavailable` | `unavailable` |
| `read_only` | reload sem trava (melhor esforço) | `memory_read_only` | `read_only` (alertas não avaliados) |

Mudança em relação a hoje: `unavailable` deixa de ser permanente no
processo — o próximo reload que encontrar um arquivo válido volta para
`available` (FR-003).

## Transição de alerta sob concorrência

`active → triggered` só é aplicada se, **depois do reload sob a trava**, o
alerta ainda estiver `active`. Duas sessões concorrentes com a mesma
cotação: a primeira dispara e persiste; a segunda recarrega, vê
`triggered` e não dispara de novo (US1 cenário 3).

## Configuração do processo

| Variável | Valores | Default | Inválido |
|---|---|---|---|
| `WALLET_MASK_VALUES` | `1`/`true`/`yes`/`on` → ligado; `0`/`false`/`no`/`off` → desligado (case-insensitive, aparado) | desligado | aborta o startup com mensagem PT-BR (FR-014) |
| `WALLET_MEMORY_PATH` | caminho | `~/.investidor10/memory.json` | inalterado; o cwd nunca é inspecionado (FR-029) |

Timeout da trava: 5 s, constante interna (sem env var nesta feature).

## Envelope mascarado

```json
{"cached": false, "fetched_at": "...",
 "privacy": {"masked": true, "omitted": ["applied", "equity", "profit_amount", "profit_twr_12m_amount"]},
 "data": {"type": "...", "variation": "...", "profit_twr": "...", "profit_twr_12m": "...", "currency": "BRL"}}
```

`omitted` lista os nomes de campo removidos **nesta** resposta (união sobre
todas as linhas, em ordem alfabética), para o modelo saber o que não tem
sem receber valores. A allowlist por tool está em
[contracts/privacy-mode.md](contracts/privacy-mode.md).
