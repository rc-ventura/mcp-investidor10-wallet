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
