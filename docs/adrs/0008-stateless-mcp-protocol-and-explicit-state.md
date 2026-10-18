# ADR-0008: Stateless MCP protocol (revision 2026-07-28) — explicit state alignment

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user

## Context

Protocol revision **2026-07-28** made MCP stateless at the protocol layer
through two combined SEPs:

- **SEP-2575** removed the `initialize`/`notifications/initialized` handshake.
  Every request now carries the protocol version and client capabilities in
  `_meta` (`io.modelcontextprotocol/protocolVersion`,
  `io.modelcontextprotocol/clientCapabilities`), and servers identify
  themselves in each result's `_meta`. `server/discover` is the optional
  up-front version-selection RPC; version mismatches return
  `UnsupportedProtocolVersionError`.
- **SEP-2567** removed protocol-level sessions and the `Mcp-Session-Id`
  header from Streamable HTTP. Cross-call state must now use **explicit,
  server-minted handles passed as ordinary tool arguments** (canonical
  example: `create_basket()` returns a `basket_id` threaded through later
  calls). List endpoints no longer vary per connection and become cacheable.

The motivation is documented in the SEP itself: after more than a year in the
spec, sessions never converged on a consistent meaning across clients — some
scoped them per tool call, per application launch, or per page load, and
almost none resumed them. A server author could not predict a session's scope
or lifetime, which made it unreliable as a container for application state,
broke load balancing without session affinity, and lost all state on restart.

This server's design assumed a **logical session**: `get_session_context` is
the mandatory first call that loads the memory digest and evaluates price
alerts (ADR-0006). The question this ADR settles is whether the stateless
revision invalidates that assumption.

## Decision

1. **No architecture change.** This server never used protocol sessions,
   `Mcp-Session-Id`, or `ctx.set_state`. The state lives in the versioned
   `memory.json` store and is surfaced through explicit tools — which is
   exactly the pattern SEP-2567 prescribes (server-side state + tool-mediated
   access), minus the handle, which is unnecessary in the single-user scope
   (there is nothing to isolate).

2. **"Session start" is officially a convention.** `get_session_context`
   remains the mandatory bootstrap tool, enforced by docstring and contract
   documentation — not by the protocol, which now formally acknowledges that
   the model decides what state to carry. This was already true in practice;
   the revision makes it the recommended architecture rather than a
   workaround.

3. **Idempotency is the session-boundary mechanism.** With no reliable
   session-start event, correctness comes from state machines, not session
   detection: `triggered` is a terminal persisted state, so calling
   `get_session_context` multiple times in one conversation is harmless —
   each alert fires once and only once (SC-006). Alert delivery is deferred,
   never lost or duplicated, if a session skips the bootstrap.

4. **Version compatibility is tracked, not chased.** The pinned
   `fastmcp==4.0.10` (ADR-0001 §4) speaks a pre-2026-07-28 protocol revision.
   Upgrades follow the existing policy (pinned versions published ≥7 days
   prior, scoped-advisory posture per ADR-0004 §8). The FastMCP framework
   absorbs protocol revisions — e.g. `UserSession`/`SessionId` primitives
   implementing SEP-2567 — so adaptation stays a dependency bump, not a
   rewrite.

## Alternatives considered

- **Keep relying on protocol sessions** — impossible: they were removed from
  the spec, and even before removal they were unreliable across clients.
- **Adopt explicit state handles / multi-user isolation now** (e.g. a
  `session_id` tool argument, FastMCP `SessionId`) — rejected: adds surface
  for zero gain in the single-user stdio scope; becomes relevant only under
  the revisit conditions below.
- **Server-side `_bootstrapped` enforcement flag** (other tools error until
  `get_session_context` runs) — deferred: it assumes one session per process,
  which holds today on stdio but is fragile; the idempotent design already
  bounds the damage of a skipped bootstrap to deferred alerts, never corrupt
  or duplicated state.

## Consequences

- SC-006 delivery depends entirely on the model honoring the tool contract —
  the protocol now offers no stronger mechanism, and none existed reliably
  before either.
- Stateless-by-default removes nothing this server depends on; stdio
  single-user operation is unaffected.
- If the server ever moves to HTTP transport or multi-user, `memory.json`
  must be replaced by a principal-keyed store (the FastMCP `UserSession`
  pattern) and alert/memory tools must take an explicit handle — this ADR's
  revisit conditions.
- This decision should be **revisited** if: the transport moves off stdio;
  the user base grows beyond the single user; or a client requires the
  2026-07-28 revision and the pinned FastMCP cannot negotiate it.
- Related: ADR-0001 (platform/pinning), ADR-0002 (persistence boundary),
  ADR-0004 (threat model), ADR-0006 (embedded memory + bootstrap).

## References

- [MCP specification changelog — revision 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [SEP-2567: Sessionless MCP via Explicit State Handles](https://modelcontextprotocol.io/seps/2567-sessionless-mcp)
- [SEP-2575: Make MCP Stateless](https://modelcontextprotocol.io/seps/2575-stateless-mcp)
- [FastMCP PR #4604 — `UserSession`/`SessionId` stateless session primitives](https://github.com/PrefectHQ/fastmcp/pull/4604)
- [python-sdk issue #1180 — session affinity failures on k8s](https://github.com/modelcontextprotocol/python-sdk/issues/1180)
- [fastmcp issue #3073 — in-memory sessions lost on restart](https://github.com/jlowin/fastmcp/issues/3073)
