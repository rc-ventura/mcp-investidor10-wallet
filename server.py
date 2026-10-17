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

    Use together with get_wallet_positions to analyze rebalancing (FR-007):
    compare each position's percent_wallet against its percent_ideal, order the
    deviations by magnitude (SC-003, 0.1 percentage-point precision), and when
    suggesting new contributions prioritize assets below their ideal percent
    that carry a positive `buy` flag from the source. Never suggest selling an
    asset unless the user explicitly asks for it; if the wallet is aligned with
    the ideal, say so instead of forcing suggestions. This is also a data
    envelope — always mention `fetched_at` and `cached` when presenting the
    numbers.
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

    For on-demand asset REPORTS (FR-012): start from the position data here,
    add the current quote via get_asset_quote, then enrich with recent events
    from your own web search, citing every source; if no relevant recent news
    exists, say so explicitly instead of padding with generic content.
    """
    try:
        return await wallet_client.wallet_client.get_positions(asset_type)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_asset_quote(ticker: str) -> dict:
    """Current market quote and fundamentals of a ticker (any asset, in the
    wallet or not): price, day and 12-month variation, Graham and Bazin fair
    prices, P/E, P/BV, dividend yield and sector.

    Args:
        ticker: Asset ticker (e.g. PETR4, MXRF11, IVVB11). Any case accepted.

    IMPORTANT presentation rules: quotes from the B3 have an inherent delay of
    ~15 minutes — always state this when giving prices. Always mention
    `cached`/`fetched_at` (the response is a data envelope). When the ticker is
    also in the wallet, cross the quote with the position's average price using
    get_wallet_positions. Unknown tickers return a ticker_not_found error with
    a spelling suggestion — never guess another ticker. Non-B3 assets (FIIs,
    international ETFs, crypto, treasury) return asset_type_not_supported.

    For on-demand asset REPORTS (FR-012): combine this quote and the wallet
    position (when held) with recent events found through your own web search,
    citing every source; if no relevant recent news exists, say so explicitly
    instead of padding the report with generic content.
    """
    try:
        return await wallet_client.rest_client.get_quote(ticker)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_earnings(start_date: str | None = None, end_date: str | None = None) -> dict:
    """Earnings (dividends, interest, income) received by the wallet in a period.

    Args:
        start_date: YYYY-MM-DD. Omit both dates to get the last 12 months.
        end_date: YYYY-MM-DD. Must be after start_date — an inverted range
            returns an invalid_params error (never a silent empty result).

    Presentation rules: present the total and per-asset breakdown for exactly
    the requested window; a period without earnings is not an error — state it
    plainly. To compute yield on cost, cross per-asset earnings with the
    position's average price from get_wallet_positions. Always mention
    `cached`/`fetched_at`.
    """
    try:
        return await wallet_client.wallet_client.get_earnings(start_date, end_date)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_patrimony_history(months: int) -> dict:
    """Monthly patrimony evolution over a horizon, separating contributions
    from capital gains.

    Args:
        months: Positive integer horizon (e.g. 12, 24, 60).

    Presentation rules: show the monthly series splitting what was contributed
    from what the market added; when the user asks "how did my patrimony
    evolve", propose a horizon if none was given. Always mention
    `cached`/`fetched_at`.
    """
    try:
        return await wallet_client.wallet_client.get_patrimony_history(months)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def create_price_alert(ticker: str, direction: str, limit_price: float) -> dict:
    """Register a price alert for an asset. The alert is evaluated at the start
    of the NEXT session by get_session_context — there is no continuous
    monitoring outside sessions (scope of this product).

    Args:
        ticker: Asset ticker (uppercase-normalized).
        direction: 'above' (notify when price >= limit) or 'below'
            (notify when price <= limit). Boundaries are inclusive.
        limit_price: Price threshold, must be greater than zero.

    Note: quotes only exist for B3 stocks; alerts on other asset classes stay
    active but are reported as pending check (asset_type_not_supported).
    """
    try:
        return memory.create_price_alert(ticker, direction, limit_price)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def list_price_alerts(state: str | None = None) -> dict:
    """List registered price alerts, optionally filtered by state
    ('active', 'triggered', 'cancelled').

    Args:
        state: Optional filter; omit to list all alerts.
    """
    try:
        return {"alerts": memory.list_price_alerts(state)}
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)


@mcp.tool
async def cancel_price_alert(alert_id: int) -> dict:
    """Cancel an active price alert. Triggered or already-cancelled alerts
    cannot be cancelled.

    Args:
        alert_id: The id returned by create_price_alert or list_price_alerts.
    """
    try:
        cancelled = memory.cancel_price_alert(alert_id)
    except MEMORY_ERRORS as exc:
        return _memory_or_param_error(exc)
    if cancelled is None:
        return _not_found(f"Price alert {alert_id} not found")
    return cancelled


# ---------------------------------------------------------------------- memory tools


def _parse_quote_price(data) -> float | None:
    """Extract the current price from a quote payload, or None when unavailable."""
    try:
        raw = data["variation_day"]["last_quotation"]
        if isinstance(raw, (int, float)):
            return float(raw)
        return float(str(raw).replace(",", "."))
    except (KeyError, TypeError, ValueError):
        return None


@mcp.tool
async def get_session_context() -> dict:
    """Session bootstrap — MUST be called at the very start of every new session,
    before answering anything about the wallet.

    Returns the full investor memory (goal, theses grouped by ticker, personal
    rules, pending decisions, recently communicated insights) AND evaluates the
    active price alerts against current quotes: satisfied alerts are marked
    'triggered' (persisted, terminal — they never fire again) and returned in
    `triggered_alerts` so you can notify the user at the start of the session,
    with the alert's registration date and the current price. Alerts whose
    quote could not be fetched are returned in `pending_check` and remain
    active. Use `pending_decisions` to follow up on earlier recommendations and
    `recent_insights` to never repeat an alert as if it were new. If
    memory_status is "unavailable", tell the user memory could not be loaded
    and keep operating without it.
    """
    try:
        digest = memory.session_digest()
    except MemoryUnavailableError:
        return {"memory": None, "triggered_alerts": [], "pending_check": [], "memory_status": "unavailable"}

    try:
        quotes: dict = {}
        pending_check: list = []
        for alert in memory.list_price_alerts("active"):
            ticker = alert["ticker"]
            if ticker in quotes:
                continue  # one quote per ticker, reused across its alerts
            try:
                envelope = await wallet_client.rest_client.get_quote(ticker)
                quotes[ticker] = _parse_quote_price(envelope["data"])
            except wallet_client.SourceError as exc:
                pending_check.append({"ticker": ticker, "reason": exc.code})
        triggered = memory.evaluate_alerts(quotes)
    except MemoryUnavailableError:
        # The store degraded mid-session (e.g. file corrupted after boot):
        # degrade gracefully instead of leaking an exception.
        return {
            "memory": digest,
            "triggered_alerts": [],
            "pending_check": [],
            "memory_status": "unavailable",
        }
    return {
        "memory": digest,
        "triggered_alerts": triggered,
        "pending_check": pending_check,
        "memory_status": "ok",
    }


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
