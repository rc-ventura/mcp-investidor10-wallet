# ADR-0006: Embedded domain memory with a deterministic session bootstrap

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user (SDD final review cycle 4, spec 001; original user decision 2026-10-10, research D4)

## Context

The spec requires long-term investor memory (FR-008/FR-009), recommendation
history with outcomes (FR-010) and price alerts verified at session open with
no duplicate deliveries (FR-011/SC-006). The main open design question at
planning time was where this memory should live: inside this server as domain
tools, or in a separate generic MCP memory server. The decision was taken with
the user on 2026-10-10 and recorded in research D4 — but as a planning-time
note, invisible to the review pipeline, which reads `docs/adrs/`. Review cycles
have repeatedly verified alert-delivery and persistence semantics against
ADR-0002 without the *why* of the embedded architecture being recorded.

## Decision

1. **Memory lives in this server**, implemented as its own set of FastMCP tools
   backed by the local versioned `memory.json` store (`memory_store.py`;
   boundary semantics in ADR-0002).

2. **One deterministic bootstrap tool**: `get_session_context` is the mandatory
   first call of every session (documented in its docstring and the contract).
   It loads the memory digest (goal, theses by ticker, rules, pending
   decisions, recent insights) **and** evaluates active price alerts against
   current quotes in the same call — alert delivery therefore does not depend
   on the model remembering to check anything (SC-006: 100% delivery).

3. **Domain schema with state machines**: alerts (`active → triggered |
   cancelled`, terminal states) and decisions
   (`pending → accepted | rejected | postponed`) need structured state that a
   generic knowledge graph cannot guarantee; the store owns it (data-model.md).

4. **No overlap with the harness**: Devin/Claude Code's generic memories remain
   the place for free-form narrative notes; this store covers only structured
   investor domain knowledge.

## Alternatives considered

- **Separate generic MCP memory server** (`@modelcontextprotocol/server-memory`)
  — rejected: recall would depend on the model reading the graph each session
  (silent failure), and alert state machines have no home there.
- **Hybrid (structured here + notes in the generic server)** — rejected: two
  stores to maintain; the harness already covers free-form notes.
- **A separate `check_alerts` tool** — rejected: the model could forget to call
  it; embedding evaluation in the bootstrap is the only path that guarantees
  SC-006.

## Consequences

- SC-004/SC-005/SC-006 depend on the deterministic bootstrap: memory recall and
  alert delivery are guaranteed by tool behavior, not by model discipline.
- The store is the single source of truth for domain state; a future migration
  to SQLite (research D5) must preserve ADR-0002's semantics (unique positive
  IDs per collection, all-or-nothing trigger persistence).
- This decision should be **revisited** if: memory must sync across machines or
  users (cloud store), or the harness standardizes a memory substrate with the
  same determinism guarantees.
- Related: ADR-0002 (persistence boundary), ADR-0007 (tool interface contract),
  research D4/D7.