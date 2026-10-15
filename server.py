"""MCP server: Investidor10 wallet agent with long-term investor memory.

Runs over stdio (the agent client spawns this process; no network exposed).
Tool registration happens per user story; this module owns the app instance,
the shared memory store, and the structured error helpers used by all tools.

Specs: specs/001-mcp-investidor10-wallet/ (plan.md, contracts/mcp-tools.md)
"""

import os

import wallet_client
from fastmcp import FastMCP
from memory_store import MemoryStore, MemoryUnavailableError

mcp = FastMCP("investidor10-wallet")

memory = MemoryStore(os.getenv("WALLET_MEMORY_PATH", "memory.json"))


def source_error_payload(exc: wallet_client.SourceError) -> dict:
    """Convert a data-source failure into the structured error envelope."""
    return exc.to_payload()


def memory_error_payload(exc: MemoryUnavailableError) -> dict:
    """Convert a memory-store failure into the structured error envelope.

    The agent should inform the user and keep operating without memory
    (spec edge case: corrupted memory must not disable the other tools).
    """
    return {"error": {"code": "memory_unavailable", "message": str(exc)}}


def _memory_or_param_error(exc: Exception) -> dict:
    if isinstance(exc, MemoryUnavailableError):
        return memory_error_payload(exc)
    return {"error": {"code": "invalid_params", "message": str(exc)}}


def _not_found(what: str) -> dict:
    return {"error": {"code": "not_found", "message": what}}


MEMORY_ERRORS = (MemoryUnavailableError, ValueError)


# --------------------------------------------------------------------- wallet tools


@mcp.tool
async def get_wallet_summary() -> dict:
    """Overview of the configured wallet: applied amount, patrimony (equity),
    variation, and total and 12-month returns.

    Use this first when the user asks "how is my wallet doing?". The response is
    a data envelope: always tell the user the data freshness by mentioning
    `fetched_at` and whether the answer came from the in-memory cache
    (`cached=true`). On failure this returns {"error": {"code", "message"}} —
    never invent values.
    """
    try:
        return await wallet_client.wallet_client.get_summary()
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_wallet_allocation() -> dict:
    """Wallet allocation broken down by asset (ticker) and by asset class.

    Use together with get_wallet_positions to compare the current allocation
    against the ideal one. This is also a data envelope — always mention
    `fetched_at` and `cached` when presenting the numbers.
    """
    try:
        return await wallet_client.wallet_client.get_allocation()
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_wallet_positions(asset_type: str) -> dict:
    """Detailed positions of one asset class of the wallet.

    Args:
        asset_type: One of Ticker (Brazilian stocks), Fii (real estate funds),
            EtfInternational (international ETFs), Treasure (Brazilian treasury
            bonds), Crypto. Any case is accepted; other values return an
            invalid_asset_type error listing the valid types.

    Each position includes quantity, average price, current quote, equity,
    profitability, percent of wallet (percent_wallet), ideal percent
    (percent_ideal), fundamental indicators when the class provides them
    (P/E, P/B, dividend yield, ROE) and the source's buy flag. A class with no
    positions returns data as an empty list (not an error). Never invent
    indicator values that the source did not provide.

    Presentation rules: compare percent_wallet vs percent_ideal when discussing
    rebalancing; for EtfInternational positions, remind the user that equity
    involves currency conversion; always mention `cached` and `fetched_at`.
    """
    try:
        return await wallet_client.wallet_client.get_positions(asset_type)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


# ---------------------------------------------------------------------- memory tools


@mcp.tool
async def get_session_context() -> dict:
    """Session bootstrap — MUST be called at the very start of every new session,
    before answering anything about the wallet.

    Returns the full investor memory (goal, theses grouped by ticker, personal
    rules, pending decisions, recently communicated insights) plus any price
    alerts triggered since the last session. Use `pending_decisions` to follow
    up on earlier recommendations and `recent_insights` to never repeat an
    alert as if it were new. If memory_status is "unavailable", tell the user
    memory could not be loaded and keep operating without it.
    """
    try:
        return {"memory": memory.session_digest(), "triggered_alerts": [], "memory_status": "ok"}
    except MemoryUnavailableError:
        return {"memory": None, "triggered_alerts": [], "memory_status": "unavailable"}


@mcp.tool
async def get_wallet_goal() -> dict:
    """Read the investor's declared wallet goal (e.g. retirement target)."""
    try:
        return {"wallet_goal": memory.get_wallet_goal()}
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def set_wallet_goal(text: str) -> dict:
    """Set or update the investor's wallet goal. Call when the user states or
    revises the purpose of the wallet (e.g. 'this wallet is for retirement').

    Args:
        text: The goal statement in the user's own words.
    """
    try:
        return memory.set_wallet_goal(text)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def save_thesis(ticker: str, text: str) -> dict:
    """Record an investment thesis the user explained for an asset. Call this
    whenever the user describes WHY they hold (or want) an asset, so it can be
    recalled in future sessions with its date. The ticker is normalized to
    uppercase and multiple theses per ticker are kept as history.

    Args:
        ticker: Asset ticker (e.g. PETR4, MXRF11).
        text: The thesis, in the user's own reasoning.
    """
    try:
        return memory.save_thesis(ticker, text)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def get_theses(ticker: str | None = None) -> dict:
    """List recorded investment theses, optionally filtered to one ticker.
    Call when discussing an asset to recall its thesis with the recording date.

    Args:
        ticker: Optional ticker filter (any case accepted).
    """
    try:
        return {"theses": memory.get_theses(ticker)}
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def save_rule(text: str) -> dict:
    """Record a personal investment rule of the user (e.g. 'only buy with a
    positive rating', 'minimum dividend yield of 6%'). Call this when the user
    states a rule that should guide every future suggestion.

    Args:
        text: The rule in the user's own words.
    """
    try:
        return memory.save_rule(text)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def get_rules() -> dict:
    """List the user's personal investment rules. Respect them in every
    suggestion you make."""
    try:
        return {"rules": memory.get_rules()}
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def log_decision(
    kind: str, content: str, ticker: str | None = None, rationale: str | None = None
) -> dict:
    """Log a recommendation you made or a decision the user made, with today's
    date and outcome='pending'. ALWAYS log recommendations when you give them,
    so the outcome can be recorded later and the recommendation is never
    repeated blindly. Never re-recommend something the user rejected without a
    new, explicit rationale.

    Args:
        kind: 'recommendation' (yours) or 'user_decision' (theirs).
        content: What was recommended/decided.
        ticker: Optional related ticker.
        rationale: Optional reasoning behind it.
    """
    try:
        return memory.log_decision(kind, content, ticker=ticker, rationale=rationale)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def record_decision_outcome(decision_id: int, outcome: str, note: str | None = None) -> dict:
    """Record the outcome of a logged decision when the user tells what they
    did about it. Outcomes: 'accepted', 'rejected', 'postponed'.

    Args:
        decision_id: The id returned by log_decision.
        outcome: accepted | rejected | postponed.
        note: Optional context (e.g. why it was rejected).
    """
    try:
        updated = memory.record_decision_outcome(decision_id, outcome, note=note)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)
    if updated is None:
        return _not_found(f"Decision {decision_id} not found")
    return updated


@mcp.tool
async def log_insight(kind: str, fingerprint: str, summary: str) -> dict:
    """Log an insight or alert AFTER communicating it to the user, so it is
    never presented again as new. `fingerprint` is a stable key you derive from
    the insight content (e.g. 'PETR4:15.2>8.0'). If it was already logged, the
    response has already_logged=true and NOTHING is duplicated — in that case
    mention the condition persists instead of alerting again.

    Args:
        kind: Insight category (e.g. concentration_alert, rebalancing).
        fingerprint: Stable dedupe key derived from the insight.
        summary: Short description of what was communicated.
    """
    try:
        return memory.log_insight(kind, fingerprint, summary)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


if __name__ == "__main__":
    mcp.run()
