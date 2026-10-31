# ADR-0003: Stale-cache age policy and boundary-semantics unification

- **Status**: Accepted (amended 2026-10-29)
- **Date**: 2026-10-17
- **Deciders**: Tech Leader (SDD final review cycle 3, spec 001)

## Context

Review cycle 3 found the remaining weaknesses shared one pattern: validation
applied endpoint-by-endpoint instead of as a uniform rule. Two findings sat on
success-criterion paths, and cycle-2 mandatory items 4 and 5 were only
partially closed:

- the 5xx/transport stale-cache fallback served entries of **unbounded age**
  (US1 sc.4 promises "recent cached data", but neither a bound nor an explicit
  spec change was recorded — the cycle-2 test even locked in serving a
  ~3-hour-old entry);
- the pagination merge double-counted rows when the source ignored `start`,
  and a fixed `max_pages=20` cap silently truncated classes at 1000 rows while
  `merged["total"]` still claimed the source total (SC-002 risk);
- `get_summary` validated `applied`/`equity` by presence only (cycle-2
  mandatory item 4, half closed); `get_quote` mapped any non-dict payload to
  `ticker_not_found`; invalid `WALLET_ID`/`WALLET_CACHE_TTL_SECONDS` crashed
  the server at import with a raw traceback; persisted alerts with
  regex-invalid tickers were reported with the caller-facing `invalid_params`
  shape instead of the contract's `invalid_alert` shape.

## Decision

1. **Bounded stale-cache fallback**: on HTTP 5xx or transport error, an
   expired cache entry is served only while its age is at most
   `WALLET_CACHE_MAX_STALE_SECONDS` (default `86400` = 24h, env-configurable,
   finite number >= 0). Older entries fail with `source_unavailable` stating
   the entry age and the bound. The age disclosure (`fetched_at`,
   `cached=true`) is kept, but disclosure alone no longer counts as "recent".

2. **Pagination merge semantics**: `get_positions` walks pages of 50 until the
   source `total`, without a fixed page cap. Rows are deduplicated by ticker
   (full-row identity when the row has no ticker); the loop stops on a page
   that adds no new rows, a short page (fewer than 50), or when the collected
   unique rows reach `total`. The merged `total` reflects the unique rows
   actually collected — never more than `data` contains. A missing/non-int
   source `total` is tolerated: pagination then stops on the short page.

3. **Structured startup failure for env config**: a non-numeric `WALLET_ID`,
   or a non-finite/negative/non-numeric `WALLET_CACHE_TTL_SECONDS` /
   `WALLET_CACHE_MAX_STALE_SECONDS`, aborts startup with `SystemExit` (exit
   code 1) carrying a clear, actionable message — no raw import-time
   traceback. This mirrors the memory store's degraded-mode philosophy: the
   operator is told exactly what to fix.

4. **Nested numeric validation for the summary**: `get_summary` requires
   `applied` and `equity` to be numeric — a finite number or a string parsing
   as a finite number (the live source returns numeric strings such as
   `"96801.5575437"`; bools excluded). Invalid values raise
   `unexpected_format` and never enter the cache.

5. **Quote payload mapping**: only a genuinely empty payload (empty JSON
   object) maps to `ticker_not_found` (T026). Any non-empty non-dict payload
   (array, null, string, number) maps to `unexpected_format` — schema drift,
   not a missing ticker.

6. **Single source of truth for ticker validity**: the shared
   `memory_store.TICKER_PATTERN` (`[A-Z][A-Z0-9]{3,11}`, applied to the
   uppercase-normalized ticker) is used by both `create_price_alert` and
   `alert_is_valid`. Persisted alerts with regex-invalid tickers are reported
   in `pending_check` with the contract's `invalid_alert` shape
   (`{"alert_id", "reason"}`), never the caller-facing `invalid_params` shape.
   Hand-edited lowercase tickers remain valid (the check normalizes first).

## Consequences

- The 5xx fallback now degrades from "stale data" to "explicit error" after
  the max-stale age — callers must handle `source_unavailable` during
  prolonged outages.
- `merged["total"]` is no longer the raw source total; it is the honest count
  of collected unique rows (equal to the source total whenever pagination
  works normally).
- Startup misconfiguration produces a one-line actionable error instead of a
  traceback; the `WalletClient` constructor still raises `SourceError` for
  direct (in-process) construction.
- Operators can tighten `WALLET_CACHE_MAX_STALE_SECONDS` for fresher data
  guarantees (e.g. `3600` for 1h).
## Emenda 2026-10-29 (revisão final da spec 004, ciclo 3)

**A paginação de posições ganha um limite absoluto.** O §2 tirou o teto fixo de
páginas e confiou nas guardas de progresso. Uma fonte com defeito ou hostil que
devolve sempre 50 linhas novas, sem `total` ou com `total` inflado, mantinha o
laço girando para sempre, com memória crescendo e requisições sem fim. Agora a
coleta para em `MAX_POSITION_PAGES` (400 páginas, 20 mil linhas), muito acima
de qualquer carteira real, e marca `truncated: true`. O resto do §2 continua:
`total` nunca afirma mais linhas do que `data` contém. O sinal `truncated`,
criado para a fonte que ignora `start`, cobre os dois casos.

## Emenda 2026-10-29 (revisão final da spec 004, ciclo 4)

**O `total` declarado pela fonte é um dado a validar, não um limite confiável
do laço.** `get_positions` adotava qualquer `int` como total. Com `total=0`,
negativo ou menor que a primeira página cheia, `len(rows) >= total` encerrava a
coleta na página 1 e `len(rows) < total` dava falso: `truncated: false` sobre
uma lista parcial, justamente o caso que o sinal existe para marcar. Agora só
um inteiro positivo é adotado, e um total que as linhas coletadas superam é
descartado, porque já se provou errado. Sem total válido, as guardas de página
curta, de progresso e de `MAX_POSITION_PAGES` encerram a coleta, e a parada
pelo teto continua marcando `truncated: true`.

## Emenda 2026-10-29 (revisão final da spec 004, ciclo 5)

**O total declarado pode mudar entre páginas, e vale o maior válido.** A emenda
do ciclo 4 adotava o total só da primeira página que o declarasse. Com a página
1 dizendo `total=100` e a página 2 dizendo `total=200`, a coleta parava em 100
linhas com `truncated: false`, sobre uma lista que a própria fonte dizia estar
incompleta. Agora cada página com total válido pode elevá-lo, e uma declaração
menor nunca o reduz: o maior total é a afirmação de completude mais exigente.
Se as linhas coletadas o superarem, ele é descartado como antes.
