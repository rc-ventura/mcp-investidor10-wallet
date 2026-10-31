# Contract — erros das tools (sinal duplo)

Emenda o contrato de erro do ADR-0007. Cobre FR-021…FR-025 e FR-036.

## Forma no protocolo

Todo erro previsto sai como `CallToolResult` com:

| Campo MCP | Valor |
|---|---|
| `isError` | `true` |
| `structuredContent` | `{"error": {"code": "<código>", "message": "<texto>"}}` |
| `content[0]` | `TextContent` com o mesmo JSON serializado (código e mensagem legíveis para clientes que só mostram texto) |

Sucesso: inalterado (`isError` ausente/`false`, mesmo `structuredContent`
e `content` de antes). Exceção inesperada: inalterada (canal do framework,
detalhe sanitizado; não ganha código do conjunto fechado).

Ponto único de emissão: middleware `on_call_tool`. Regra de detecção:
`structured_content` é dict e tem a chave de topo `error` → `isError=true`.
`ValidationError` do framework → `invalid_params` com `isError=true`, com os
nomes dos argumentos inválidos entre parênteses depois do nome da tool (nunca
os valores recebidos).

## Conjunto fechado de códigos (12)

| Código | Origem | Tentar de novo? | Próxima ação nomeada na `message` |
|---|---|---|---|
| `source_unavailable` | fonte fora do ar / HTTP ≥400 | sim, mais tarde | repetir a mesma tool depois; se 4xx, conferir `WALLET_ID` |
| `unexpected_format` | drift de schema da fonte | não | informar o usuário; não usar números |
| `invalid_asset_type` | `get_wallet_positions` | sim, corrigindo | repetir com um dos tipos listados |
| `ticker_not_found` | `get_asset_quote` | sim, corrigindo | conferir a grafia do ticker |
| `asset_type_not_supported` | `get_asset_quote` (HTTP 410) | não | usar `get_wallet_positions` para ativos da carteira |
| `invalid_params` | validação de argumentos | sim, corrigindo | conferir o schema da tool nomeada |
| `memory_unavailable` | memória inválida/inacessível | não nesta sessão | seguir sem memória; avisar o usuário |
| `not_found` | id inexistente em alerta/decisão | sim, corrigindo | `list_price_alerts` / `get_session_context` para ver ids válidos |
| `memory_busy` **(novo)** | trava não obtida em 5 s | sim, em instantes | repetir a mesma tool |
| `memory_read_only` **(novo)** | FS sem suporte a trava | não | avisar o usuário; leituras seguem funcionando |
| `state_conflict` **(emenda 2026-10-28)** | `cancel_price_alert` em alerta já disparado ou cancelado | não com o mesmo id | `list_price_alerts` para conferir estados; criar alerta novo com `create_price_alert` |
| `privacy_mode_unavailable` **(novo)** | `get_patrimony_history`, `get_earnings` com modo privacidade | não | explicar que o operador ligou o modo privacidade; usar `get_wallet_allocation`/`get_wallet_positions` para análise por percentual |

Não há campo `retryable`/`category` (decisão D7): a retentabilidade é
função do código e está nesta tabela; a `message` carrega a próxima ação.

## Estilo das mensagens (FR-023)

Inglês (ADR-0009). Forma: **recurso + causa + próxima ação**, nomeando
tool do servidor quando houver. Exemplos-alvo:

- `memory_busy`: "Investor memory is locked by another server process
  (another client is writing). Retry the same tool call in a moment."
- `memory_read_only`: "Investor memory at <path> is read-only: the
  filesystem does not support file locking, so writes are refused to avoid
  losing data. Reads still work; tell the user the operator must point
  WALLET_MEMORY_PATH to a local disk."
- `privacy_mode_unavailable`: "get_earnings is unavailable: the operator
  enabled privacy mode, which withholds monetary amounts. Use
  get_wallet_allocation or get_wallet_positions for percentage-based
  analysis; do not estimate the withheld amounts."

## Testes de contrato

- um caso por código provocando o erro e afirmando `is_error is True`,
  `structured_content["error"]["code"] == <código>` e o código presente em
  `content[0].text`;
- um caso de sucesso por tool afirmando `is_error is False` e payload
  idêntico ao snapshot anterior (SC-005);
- testes existentes que leem payload de erro via `Client.call_tool` passam
  `raise_on_error=False`.
