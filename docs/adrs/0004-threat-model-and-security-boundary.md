# ADR-0004: Threat model and security boundary of the single-user stdio server

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user (SDD final review cycle 4, spec 001)

## Context

Every security review cycle (2, 3 and 4) re-derived the same threat model from
scratch to classify findings: the indirect prompt-injection LOWs, the runtime
`memory.json` created mode 0644, malformed env crashing at import, and the
scoped FastMCP GHSAs were all judged against an unrecorded mental model of what
this server is and who can attack it. Recording that model once prevents
re-litigating the same classification every cycle and defines the boundary that
decides whether a finding is a vulnerability, an accepted design property, or an
operator error.

## Decision

1. **Deployment shape**: the server is a single-user, single-wallet process
   spawned by a local MCP client over **stdio**. It never opens a network
   listener and never runs as a service.

2. **Authentication is delegated**: the local MCP client config owns `WALLET_ID`
   (a public wallet identifier, not a secret). The server authenticates nothing
   and trusts the local operator — whoever can edit the client config or the
   local files is already in the trust boundary.

3. **Fixed outbound surface**: the only network egress is
   `https://investidor10.com.br` (wallet proxy + REST assets). There are no
   user-controlled URLs; `WALLET_ID` is validated digits-only and tickers pass a
   charset allowlist (`[A-Z][A-Z0-9]{3,11}`) before any URL is built — closing
   the URL/path-injection path.

4. **No secrets**: no API keys, tokens or credentials exist anywhere in the
   system; nothing is written to logs.

5. **Local memory is trusted data**: `memory.json` is user-authored local data,
   treated like any other local config. Corrupted files degrade the store
   instead of crashing (ADR-0002). Memory text and upstream JSON are returned
   verbatim to the agent LLM at session bootstrap — an accepted indirect
   prompt-injection surface inherent to the product (a memory assistant); this
   server executes nothing.

6. **On-disk integrity**: atomic writes via private 0600 temp files +
   `os.replace`, backups `.broken-*` 0600/O_EXCL (ADR-0002), bounded stale
   cache (ADR-0003). The one-time `chmod 600 memory.json` applied in cycle 4
   aligned the pre-hardening runtime file with the new 0600 writes.

7. **No side effects**: all calls to the source are read-only GETs; the server
   never places orders (spec assumption: suggestions only, execution is the
   user's).

8. **Dependency posture**: fastmcp and httpx pinned (research D9). The Oct-2026
   FastMCP GHSAs in range for 4.0.10 affect client/OpenAPI surfaces this server
   never instantiates — accepted as scoped risk with a scheduled tested upgrade
   to >=4.1.0 as hardening.

## Consequences

- Security findings are classified against this model: misconfiguration by the
  local operator (bad env, loose file perms) is not an attacker boundary;
  anything requiring a network listener, multi-user access, secrets, new
  outbound hosts, or order execution WOULD be.
- The single-user scope keeps auth, rate limiting and audit logging out of the
  product by design (A01/A04/A09 do not apply at this boundary).
- This decision should be **revisited** if: the server gains a network
  transport or multi-user scope; outbound hosts grow beyond investidor10.com.br
  (e.g. an international quotes source per the learning lesson
  `get_asset_quote_apenas_acoes_b3`); secrets are introduced; or web-fetched
  content starts being executed or written to disk by this process.