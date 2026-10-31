# ADR-0014: Sinal duplo de erro — `isError` do protocolo mais o envelope estruturado

- **Status**: Accepted (amended 2026-10-28)
- **Date**: 2026-10-28
- **Deciders**: Tech Leader + User (ciclo spec 004)
- **Related spec**: [`specs/004-hardening/`](../../specs/004-hardening/)
- **Code**: `src/investidor10_wallet/server.py` (`ErrorSignalMiddleware`, `source_error_payload`, `NEXT_ACTIONS`)
- **Research**: `docs/research/tool-error-channels.md`; `specs/004-hardening/contracts/error-envelope.md`

---

## Context

O ADR-0007 decidiu que todo erro previsto sai como `{error: {code, message}}`
dentro de uma resposta normal da tool (canal C da pesquisa). No metadata do
protocolo, porém, essas chamadas constavam como sucesso: um cliente ou modelo
que olha só o sinal de erro do protocolo não percebia a falha, o mesmo modo de
falha documentado em apache/superset#43358. A Constituição (II.1) já previa a
evolução para sinal duplo, alinhada à direção da spec MCP (SEP-1303/SEP-2145:
tudo que o modelo pode corrigir é *tool execution error*, não *protocol error*).

O `fastmcp==4.0.11` suporta isso: `ToolResult(..., is_error=True)` mantém o
`structured_content` e mapeia para `CallToolResult.isError`
(`fastmcp/tools/base.py`), e o conteúdo textual é a serialização JSON do
`structured_content`, então código e mensagem ficam legíveis também para
clientes que só exibem texto.

## Decision

1. **Ponto único de emissão.** O middleware `ErrorSignalMiddleware`
   (`on_call_tool`) devolve `ToolResult(content, structured_content,
   is_error=True)` sempre que o `structured_content` é um dict com a chave de
   topo `error`. O `ValidationError` do framework vira `invalid_params` com
   `is_error=True`. Nenhuma tool muda de assinatura. Não há falso positivo
   possível: nenhum envelope de sucesso tem `error` no topo.
2. **Respostas de sucesso inalteradas.** Mesmo `structured_content` e mesmo
   `content` de antes.
3. **Exceção inesperada continua no canal do framework**, agora sanitizada com
   `mask_error_details=True` (o cliente recebe só `Error calling tool 'x'`) e com o
   traceback no stderr do servidor. Não ganha código do conjunto fechado
   (Constituição II.3).
4. **Conjunto fechado de 11 códigos**: os 8 anteriores (`source_unavailable`,
   `unexpected_format`, `invalid_asset_type`, `ticker_not_found`,
   `asset_type_not_supported`, `invalid_params`, `memory_unavailable`,
   `not_found`) mais `memory_busy`, `memory_read_only` e
   `privacy_mode_unavailable`.
5. **Sem campo `retryable`/`category`.** A retentabilidade é função do código
   e fica numa tabela no contrato (`error-envelope.md`); a `message` carrega a
   próxima ação. Um campo adicional seria redundante e poderia divergir do
   código.
6. **Mensagens no estilo trigger-phrase**: recurso, causa e próxima ação,
   nomeando tool do servidor quando houver (`list_price_alerts`,
   `get_session_context`, `get_wallet_positions`). Para erros da fonte, a
   próxima ação é acrescentada na conversão do servidor
   (`source_error_payload`), sem alterar o formato de `SourceError.to_payload`.

## Alternatives considered

### Alternative A: lançar `ToolError` em cada tool

**Why not chosen**:
- O `ToolError` produz `isError` mas perde o `structured_content` com o código
  estruturado, e exigiria alterar todas as tools.

### Alternative B: campo `retryable` no envelope

**Why not chosen**:
- Redundante com o código; dois lugares para manter coerentes.

### Alternative C: converter também exceções inesperadas

**Why not chosen**:
- Bug é bug: mascarar com um código "previsto" esconde a falha (Constituição II.3).

## Consequences

### Accepted

- O agente e o cliente recebem o sinal de erro do protocolo e o código
  estruturado juntos; falha deixa de parecer dado.
- Um único ponto de código garante cobertura de todas as tools, inclusive as
  futuras.

### Trade-offs

- Clientes que levantam exceção em `isError` (padrão de `fastmcp.Client.call_tool`)
  passam a exigir `raise_on_error=False` para ler o payload; os testes usam um
  wrapper fino do `Client`. `.data` não é preenchido pelo client em resultados
  de erro: ler `structured_content`.
- Comportamento por cliente (por exemplo, esconder o conteúdo de um resultado
  `isError`) varia; o texto do conteúdo carrega o JSON completo como defesa.
  O Claude Desktop é validado na spec 005.

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. A spec MCP ou o FastMCP passarem a tratar erros previstos de outra forma.
2. Algum cliente alvo descartar o conteúdo de resultados `isError`.

### Migration path when needed

1. Ajustar só o middleware (ponto único) e o contrato de erro.

## References

- ADR-0007 (envelope e erros estruturados; emendado com o conjunto de 11 códigos)
- Constituição, Princípio II.1–II.4
- `docs/research/tool-error-channels.md`
- gofastmcp.com `/clients/tools` (`CallToolResult.is_error`, `raise_on_error`)

## Emenda 2026-10-28 (pendências da revisão final da spec 004)

1. **12º código: `state_conflict`.** Cancelar um alerta que já disparou ou já
   foi cancelado não é erro de argumento: o id existe e é válido, é o estado
   que impede a operação. Antes isso saía como `invalid_params`, cuja próxima
   ação ("conferir o schema") levava o modelo a corrigir o que não estava
   errado. Agora sai como `state_conflict`, com `isError`, e a mensagem manda
   conferir os estados com `list_price_alerts` e criar um alerta novo se ainda
   for preciso. O conjunto fechado passa a ter 12 códigos (tabela em
   `specs/004-hardening/contracts/error-envelope.md`). Tentar de novo: não com
   o mesmo id.
2. **`invalid_params` nomeia o argumento.** O middleware lê os locais dos erros
   do pydantic e acrescenta os nomes dos argumentos inválidos à mensagem
   (por exemplo, `Invalid parameters for get_patrimony_history (months): ...`).
   Só nomes com forma de identificador são ecoados, nunca os valores recebidos.
