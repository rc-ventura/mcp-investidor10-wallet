# ADR-0001: Platform and storage choices — FastMCP, httpx + TTL cache, single JSON store, pinned deps

- **Status**: Accepted (amended 2026-10-28)
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user (SDD final review cycle 4, spec 001)

## Context

The platform and storage choices were decided during planning and recorded in
detail in `specs/001-mcp-investidor10-wallet/research.md` (D1, D2, D5, D9), with
rationale and alternatives per item. That document lives inside the spec folder
and is not part of the decision index (`docs/adrs/`) that the review pipeline
reads. This ADR consolidates those choices into the living decision index so
reviewers and future contributors get the full picture without reopening
research: which framework, which HTTP/caching strategy, which storage, and
which dependency policy — and why.

## Decision

1. **MCP framework: FastMCP (Python), stdio transport** (research D1, pinned
   4.0.10). Tools are registered with `@mcp.tool`; schemas are generated from
   type annotations and docstrings — and the docstrings become the description
   the LLM reads, which makes them the de-facto contract with the model
   (ADR-0007). Async tools are native; stdio matches the "client spawns the
   process" requirement (FR-015). Alternatives rejected: low-level
   `mcp.server.lowlevel` (boilerplate, no gain) and the TypeScript SDK
   (breaks the user's Python familiarity).

2. **HTTP: httpx async + in-process TTL cache** (research D2, ADR-0003 for the
   stale-cache bound). Browser User-Agent, 20s timeout; cache keyed by
   path+params with `WALLET_CACHE_TTL_SECONDS` (default 600s). An in-process
   cache suffices because the client spawns a fresh process per session —
   there is no long-lived server needing shared cache state; the short TTL
   keeps data "recent" per FR-014. Alternatives rejected: `requests`
   (blocking), `aiohttp` (verbosity), `cachetools.TTLCache` (extra dependency
   for ~15 lines of stdlib).

3. **Storage: one versioned `memory.json`, full in-memory load, atomic
   tmp+rename writes** (research D5; boundary semantics in ADR-0002). Zero
   dependencies, stdlib-only, human-readable/editable, and the expected scale
   (hundreds of entries) makes in-memory queries irrelevant. SQLite remains the
   documented migration path: the schema is already relational-friendly
   (named collections with IDs), so migrating is rewriting `memory_store.py`
   plus a trivial import script. Alternatives rejected for the MVP: SQLite
   (overkill) and Markdown+frontmatter (fragile parsing, no queries).

4. **Dependency policy: pinned, no floating ranges** (research D9).
   `fastmcp` and `httpx` pinned to versions published at least 7 days prior;
   dev deps (`pytest`, `pytest-asyncio`, `respx`) pinned as well; install/run
   via `uv`. The 7-day rule reduces supply-chain exposure to brand-new
   releases without falling behind. Scoped-advisory posture (FastMCP GHSAs
   affecting client/OpenAPI surfaces this server never instantiates) is
   recorded in ADR-0004 §8, with a scheduled tested upgrade as hardening.

## Alternatives considered

See each item above — the research already weighed and rejected the concrete
alternatives per decision (low-level SDK, TypeScript SDK, `requests`,
`aiohttp`, `cachetools`, SQLite-for-MVP, Markdown storage). None of those
rejections were reversed by later cycles.

## Consequences

- The whole runtime is two pinned dependencies plus stdlib, running in one
  process with three cohesive modules (plan.md structure decision) — the
  security surface stays exactly the fixed-host, single-user boundary of
  ADR-0004.
- Cache and memory are per-process and per-file respectively; there is no
  persistence layer to operate beyond the session lifetime.
- This decision should be **revisited** if: the process becomes long-lived
  (cache would need eviction/shared state), memory grows beyond hundreds of
  entries (SQLite migration path), the source API multiplies (bounded
  concurrency/pooling), or a framework change is needed for a network
  transport (ADR-0004 revisit conditions).
- Related: ADR-0002 (persistence boundary), ADR-0003 (cache/stale semantics),
  ADR-0004 (threat model), ADR-0007 (tool interface), research D1/D2/D5/D9.

### Emenda 2026-10-28 (spec 004)

A política de dependências do §4 ("httpx + fastmcp, pinados") ganha uma
exceção autorizada pela emenda 1.2.0 da Constituição (V.1): `filelock==4.2.4`
como dependência direta de runtime, usada só para exclusão mútua entre
processos sobre o arquivo de memória. Qualquer outra dependência de runtime
continua exigindo nova emenda. Decisão e alternativas no ADR-0013.

### Emenda 2026-10-28 (revisão final da spec 004, ciclo 2) — atualização de dependências

O §4 diz como as versões ficam fixas, mas não quando mudam. A revisão final da
spec 004 achou CVEs no lock (`fastmcp` 4.0.11, `authlib` transitivo e
`certifi` transitivo). Fica decidido:

- **Dependências diretas** (`fastmcp`, `httpx`, `filelock`) continuam com `==`
  e só mudam por bump deliberado, com a suíte completa verde antes do merge.
  Aplicado agora: `fastmcp==4.1.2` (publicado há 8 dias), que corrige as duas
  GHSAs da 4.0.11.
- **Transitivas** não têm pin no `pyproject.toml`. Elas mudam por renovação
  do `uv.lock` (`uv lock --upgrade-package <pacote>`) sempre que houver aviso
  de segurança, e a cada release. Isso não fere o §4, porque o lock continua
  determinístico. Usa-se a versão corrigida mais antiga que respeite a regra
  dos 7 dias. Aplicado agora: `authlib` 1.9.1 (14 dias) e `certifi`
  2026.10.19 (8 dias). Exceção registrada: `virtualenv` 21.14.13, dependência
  só de desenvolvimento via `pre-commit` e fora do pacote publicado, tinha 6
  dias. É a versão corrigida mais antiga do CVE-2026-115586, e esperar um dia
  manteria o job `audit` vermelho.
- **Auditoria contínua**: o job `audit` do CI roda `pip-audit` (versão fixa)
  sobre o lock exportado em todo push e PR. Um achado novo falha o CI e entra
  na renovação acima. Achados não alcançáveis só podem ser ignorados com
  justificativa registrada no ADR-0004 §8.
