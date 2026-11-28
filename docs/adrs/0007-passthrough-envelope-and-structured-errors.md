# ADR-0007: Source passthrough with data envelope and structured errors

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user (SDD final review cycle 4, spec 001)

## Context

The data tools could either re-model the source into typed domain objects or
pass the source JSON through almost raw. The data model chose passthrough
(data-model.md: "O servidor NÃO re-modela esses dados; repassa o JSON da
fonte"), and the contract adds two invariants around it: every data tool
response is enveloped with freshness metadata (`{cached, fetched_at, data}`,
FR-014) and every failure is a structured error (`{error: {code, message}}`,
FR-016) — never a raw exception to the LLM and never fabricated values. This is
the interface philosophy of the whole server, recorded so far only as spec
prose; every review cycle touches its consequences (schema-drift handling,
freshness honesty, SC-002 fidelity) without a single decision record to point
at.

## Decision

1. **Passthrough**: data tools return the source payload unchanged inside the
   envelope. The server adds validation only as a gate (shape checks before
   caching, ADR-0003) — it never transforms, aggregates or invents fields.
   Displayed values therefore match the source exactly (SC-002; rounding
   tolerance only).

2. **Freshness honesty**: every envelope carries `cached` and `fetched_at` so
   the agent can always state the data's age; docstrings mandate mentioning it
   (FR-014). The max-stale bound (ADR-0003) guarantees a fallback answer is
   never older than policy allows, or the call fails explicitly.

3. **Structured errors**: one error shape `{error: {code, message}}` with a
   closed code set (`source_unavailable`, `unexpected_format`,
   `invalid_asset_type`, `ticker_not_found`, `asset_type_not_supported`,
   `invalid_params`, `memory_unavailable`, `not_found`) — the agent reacts to
   codes, never to exception text.

4. **Docstrings are the contract with the model** (research D8): each tool's
   docstring defines when to use it, its presentation rules and field
   meanings, in English; user interaction stays pt-BR (user decision
   2026-10-10).

## Alternatives considered

- **Re-model into typed domain objects** — rejected: transformation code risks
  SC-002 drift (display vs source), duplicates the source schema, and adds
  maintenance for zero functional gain in a read-only assistant.
- **Partial passthrough with selective enrichment** — rejected: any enrichment
  the agent needs (YOC, rebalancing math, reports) is computed by the client
  model from raw data, keeping the server a thin, auditable layer.

## Consequences

- The server is a thin, auditable data layer: what the user sees traces
  directly to the source payload, and drift surfaces as `unexpected_format`
  instead of silent transformation bugs.
- The client model owns all interpretation (insights, rebalancing suggestions,
  reports) — server changes are rare and mostly validation hardening.
- This decision should be **revisited** if: multiple data sources must be
  aggregated into one normalized view (then a modeling layer becomes
  necessary), or the agent needs server-side computed metrics at scale.
- Related: ADR-0003 (validation), ADR-0005 (source risk), ADR-0006 (memory
  tools follow the same envelope-free structured-error convention for local
  operations).

## Emenda 2026-10-28 (spec 004)

O conjunto fechado de códigos do item 3 passou a ter **11** códigos: além dos
oito listados, `memory_busy` (trava da memória ocupada), `memory_read_only`
(sistema de arquivos sem suporte a trava) e `privacy_mode_unavailable` (tool
monetária com o modo privacidade ligado). Todo erro previsto agora sai também
com `isError=true` no protocolo, mantendo o envelope e o código no texto da
resposta. Decisão e alternativas no ADR-0014. Depois disso, o 12º código
`state_conflict` (alerta inativo em `cancel_price_alert`) entrou pela emenda de
28/10/2026 do ADR-0014.

Nota de 2026-10-28 (spec 004) sobre o item 4: o FastMCP serve ao modelo só o
texto da docstring **anterior** ao bloco `Args:`; o que vem depois é descartado.
As regras de uso das tools precisam, portanto, ficar antes do `Args:`, e um teste
de contrato garante isso. Ver a learning lesson
`fastmcp_docstring_descarta_texto_apos_args.md`.

## Emenda 2026-11-28 — `get_earnings` compõe três respostas da fonte (issue #51)

Decisão do mantenedor em 28/11/2026, na revisão da PR #62.

### Problema

`get_earnings` devolvia só o total do período. Havia dois efeitos:

- **Faltavam dados**: não dava para ver os proventos recebidos por mês, nem os
  futuros. Foi o que a issue #51 pediu, indicando os endpoints.
- **O total enganava**: a descrição da tool o chamava de valor recebido, mas com
  `end_date` depois de hoje a fonte soma também pagamentos ainda não feitos
  (observado na carteira testada: total = recebido + futuro).

### Antes e depois

Base: `https://investidor10.com.br/wallet/api/proxy/wallet-app`. Em carteira
restrita, o cliente acrescenta `hash=<credencial>` a cada GET. A assinatura não
mudou: `get_earnings(start_date: str | None, end_date: str | None)`, datas
`YYYY-MM-DD`; sem as duas, valem os últimos 12 meses de calendário.

**Antes**, um GET:

| Endpoint | Query | Resposta da fonte |
|---|---|---|
| `/earnings/total-period/{id}` | `start_date`, `end_date` | `{"sum": N}` |

`data` era a resposta da fonte, validada à mão (`sum` obrigatório e numérico).

**Depois**, três GETs em sequência:

| Endpoint | Query | Vira |
|---|---|---|
| `/earnings/total-period/{id}` | `start_date`, `end_date` | `data.sum` (e as demais chaves da resposta) |
| `/earnings/barchart/{id}/received` | `period_date=<start>,<end>` | `data.received` |
| `/earnings/barchart/{id}/future` | `period_date=,` | `data.future` |

A vírgula vai codificada como `%2C`. Exemplo de `data` (valores fictícios):

```json
{
  "sum": 15.0,
  "received": {
    "2026": {
      "year": 2026,
      "total": 10.0,
      "avg": 0.91,
      "months": [
        {"month": "2026-01", "categories": [], "amount": 0},
        {"month": "2026-02", "categories": {"FIIs": 10.0}, "amount": 10.0}
      ]
    }
  },
  "future": {
    "2026": {
      "year": 2026,
      "total": 5.0,
      "avg": 0.45,
      "months": [
        {"month": "2026-12", "categories": {"Ações": 5.0}, "amount": 5.0}
      ]
    }
  }
}
```

O exemplo abrevia `months`.

Comportamentos da fonte observados em 26/11/2026, numa única carteira (a API não
tem contrato publicado):

- `barchart` devolve `[]`, e não `{}`, quando não há nada; `categories` de um mês
  vazio também é `[]`.
- `future` respeita `period_date`: com uma janela que termina hoje, volta vazio.
- Provento anunciado sem data de pagamento ("Provisionado") não aparece em
  `future`.
- `received` e `future` bateram, por mês e classe, com `/earnings/list/{id}`.

### Decisão

1. **Exceção ao item 1, limitada a `get_earnings`**: o servidor monta o objeto
   `data` a partir de três respostas. Ele continua sem calcular, somar, filtrar
   ou renomear campos das respostas: as chaves do total seguem no topo, e os dois
   `barchart` entram como vieram, sob `received` e `future`. Não vale como
   permissão geral para agregar fontes; outro caso precisa de registro próprio.
2. **`future` é consultado sem filtro** (`period_date=,`), seja qual for a janela.
3. **Falha de uma consulta falha a tool inteira**, sem resultado parcial. Vale a
   regra de cache de sempre para cada consulta: em HTTP 5xx ou erro de
   transporte, uma entrada vencida de até 24h ainda é servida. A tool só falha se
   a parte afetada não tiver cache aproveitável. 3xx, 401 e 403 seguem como
   `access_denied`.
4. **Validação antes do cache**: os dois endpoints novos usam um `TypeAdapter` do
   pydantic. Cada ano precisa de `total` e `months`; cada mês, de `month`,
   `amount` e `categories`. Números são estritos e finitos (`bool` e texto são
   recusados); `[]` é aceito para vazio; campos extras passam. Formato diferente
   vira `unexpected_format`. O total mantém a validação manual.
5. **Envelope**: cada consulta tem a própria entrada de cache (TTL padrão de
   600s). `cached` é verdadeiro se alguma parte veio do cache, e `fetched_at` é o
   da parte mais antiga.

O modo privacidade não mudou: a tool responde `privacy_mode_unavailable` sem
consultar a fonte.

### Alternativas consideradas

- **Tool separada para o detalhamento** — recusada: isolaria o total de falhas
  dos endpoints novos, mas o modelo poderia consultar só o total e tratá-lo como
  recebido, que é o erro a corrigir.
- **Resultado parcial** quando um `barchart` falha — recusado: exigiria um
  formato para marcar o que faltou e mais casos de teste, e o total sozinho não
  mostra quanto já foi pago quando a janela passa de hoje.
- **`future` com a mesma janela de `received`** — recusado: na janela padrão
  viria sempre vazio.
- **`/earnings/list/{id}` com agregação no servidor** — fica para o
  `get_earnings_detailed` (por ativo). Exigiria calcular no servidor, o que o
  item 1 evita.

### Consequências

- Uma falha ou mudança de formato nos `barchart` derruba também o total, que
  antes dependia de um só endpoint (risco do ADR-0005). O `live.yml` passa a
  cobrir os três.
- São três GETs por chamada sem cache, em vez de um.
- **As partes não são um retrato único**: com caches de idades diferentes,
  `sum` pode, por até um TTL (ou mais, em indisponibilidade), não bater com
  `received` + `future`. `fetched_at` informa só a parte mais antiga.
- O ADR-0016 não muda: ele obriga a validação em tools novas. Usar a mesma
  abordagem em endpoints novos de uma tool existente foi escolha desta PR. É o
  primeiro import direto de `pydantic` em `src/`, ainda como dependência indireta
  do FastMCP (item 5 do ADR-0016; ver DT-009).

**Rever se:** o `live.yml` ou usuários mostrarem os `barchart` instáveis com o
total funcionando; ou se a diferença momentânea entre as partes confundir alguém.
