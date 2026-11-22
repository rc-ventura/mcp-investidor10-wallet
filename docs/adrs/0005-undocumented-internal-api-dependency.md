# ADR-0005: Dependence on Investidor10's undocumented internal API

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user (SDD final review cycle 4, spec 001)

## Context

The product's only data source is a set of **internal, undocumented endpoints**
of investidor10.com.br (research D3): the wallet proxy
`https://investidor10.com.br/wallet/api/proxy/wallet-app` and the REST catalog
`https://investidor10.com.br/api/rest`. The spec's assumptions already state
that the interface's stability is not guaranteed and that format changes must
surface as explicit failures (FR-016), never silent missing data. This is the
highest business risk of the project — the source can change or disappear
overnight with no contract, deprecation notice or SLA — and it was recorded
only as a research-time note and scattered README warnings, not as a living
decision that reviews and future work can lean on.

## Decision

1. **The internal API is the primary source**, used read-only, without auth,
   with a browser User-Agent, for the single-user personal/educational scope
   (spec assumption).

2. **Risk is accepted and mitigated, not hidden**: the server fails loud.
   Strict shape validation before caching (ADR-0003) turns source drift into
   `unexpected_format` with the field/path in the message; outages into
   `source_unavailable`; 410 for non-B3 classes into `asset_type_not_supported`
   (learning lesson `get_asset_quote_apenas_acoes_b3`). Values are never
   fabricated (FR-016) — the agent is always told the data failed, never given
   synthetic numbers.

3. **Traffic and outage protection**: in-process TTL cache (default 600s)
   reduces request volume, and the max-stale bound (default 24h, ADR-0003)
   caps how old a fallback answer can be during an outage, with the age always
   disclosed via `fetched_at`/`cached=true` (FR-014).

4. **Passthrough fidelity over re-modeling**: payloads are passed through raw
   (ADR-0007) so displayed values match the source exactly (SC-002), which also
   means any source change is visible immediately as drift instead of being
   masked by a transformation layer.

5. **Fallbacks deferred**: paid/alternative market APIs (brapi, Yahoo Finance
   for international assets) remain out of scope as primary sources, but the
   international-quotes gap is a known, documented path for future work
   (learning lesson `get_asset_quote_apenas_acoes_b3`).

## Alternatives considered

- **HTML scraping of the public pages** — rejected: fragile and slower than the
  JSON endpoints.
- **Paid market APIs as primary source** — rejected while the internal API
  responds; they add credentials and cost for no functional gain in this scope.
- **Silent tolerance of drift** (skip fields, best-effort parsing) — rejected:
  violates FR-016 and would let the agent present wrong numbers (SC-002).

## Consequences

- SC-002 (100% fidelity) holds only while the source behaves as mapped; the
  validation layer is the tripwire that detects when it does not.
- The product can break without notice when the source changes; recovery is
  re-mapping the endpoints in `wallet_client.py` (a single module owns all
  source access, plan.md structure decision).
- This decision should be **revisited** if: the API starts requiring auth or
  blocks the browser User-Agent; the wallet becomes private; the endpoints are
  removed or change semantics repeatedly; or the product moves beyond
  personal/educational use (which would demand a licensed data source).
- Related: ADR-0003 (validation semantics), ADR-0007 (passthrough contract),
  research D3.

## Emenda 2026-11-14 (spec 005, Lote 7: alarme semanal contra a API real)

A deriva da fonte passou a ter um alarme que não depende de alguém lembrar de
rodar os testes: `.github/workflows/live.yml` executa `uv run pytest -m live`
toda segunda-feira (`schedule`) e sob demanda (`workflow_dispatch`).

- **Carteira:** o ID vem do segredo `LIVE_WALLET_ID`, o de uma carteira pública
  fictícia, nunca a pessoal. Sem o segredo, o job falha dizendo qual cadastrar.
- **Saída sem dado do usuário:** os asserts de `tests/integration/test_live_api.py`
  imprimem só o código do erro estruturado, nunca o corpo da resposta, o ID ou a
  credencial, porque o log da CI é visível a quem abrir o repositório.
- **Escopo:** é um alarme, não um portão. O `live.yml` não bloqueia release; a
  falha sinaliza que é hora de remapear os endpoints em `wallet_client.py`.
- **Quando começa a valer:** o GitHub só dispara `schedule` e `workflow_dispatch`
  com o workflow na branch padrão (`main`), então o primeiro disparo acontece
  depois da promoção da 0.4.0 (ADR-0020, emenda de 2026-11-14; tasks T091/T092).
- **Cobertura do alarme:** vigia o que `tests/integration/test_live_api.py`
  cobre hoje. Não há teste contra uma carteira restrita, então comportamentos como
  o 301 sem `Location` (lição `proxy_301_acesso_recusado_sem_location`) seguem
  protegidos só pela fixture anonimizada.