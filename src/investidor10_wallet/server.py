import asyncio
import math
import sys

from fastmcp import FastMCP
from fastmcp.exceptions import ValidationError
from fastmcp.server.middleware import Middleware
from fastmcp.tools import ToolResult

from . import bootstrap, memory_store, privacy, wallet_client
from .memory_store import (
    MemoryBusyError,
    MemoryReadOnlyError,
    MemoryStore,
    MemoryUnavailableError,
    StateConflictError,
)

INSTRUCTIONS = (
    "Read-only access to one public Investidor10 wallet plus a persistent investor "
    "memory (theses, rules, decisions, price alerts). Start every session with "
    "get_session_context. Wallet tools return a data envelope "
    "{cached, fetched_at, data}; errors return {error: {code, message}} with isError "
    "set. B3 quotes carry ~15 minutes of delay. When privacy.masked is true, the "
    "operator withheld monetary amounts."
)

mcp = FastMCP("investidor10-wallet", instructions=INSTRUCTIONS, mask_error_details=True)


def _invalid_argument_names(exc: ValidationError) -> list[str]:
    """Names of the offending arguments, from the pydantic error locations.

    Only identifier-shaped names are echoed back; input values never are.
    """
    errors = getattr(exc.__cause__ or exc.__context__, "errors", None)
    if not callable(errors):
        return []
    names: list[str] = []
    for error in errors():
        name = next((p for p in error.get("loc", ()) if isinstance(p, str)), None)
        if name and name.isidentifier() and len(name) <= 64 and name not in names:
            names.append(name)
    return names


class ErrorSignalMiddleware(Middleware):
    async def on_call_tool(self, context, call_next) -> ToolResult:
        try:
            result = await call_next(context)
        except ValidationError as exc:
            names = _invalid_argument_names(exc)
            which = f" ({', '.join(names)})" if names else ""
            return ToolResult(
                structured_content={
                    "error": {
                        "code": "invalid_params",
                        "message": (
                            f"Invalid parameters for {context.message.name}{which}: an "
                            "argument is missing, has the wrong type or is out of range. "
                            "Check the tool input schema and call it again with corrected "
                            "arguments."
                        ),
                    }
                },
                is_error=True,
            )
        content = result.structured_content
        if isinstance(content, dict) and "error" in content:
            return ToolResult(
                content=result.content, structured_content=content, is_error=True
            )
        return result


mcp.add_middleware(ErrorSignalMiddleware())


class _LazyMemory:
    def __init__(self) -> None:
        self._store: MemoryStore | None = None

    def __getattr__(self, name: str):
        if self._store is None:
            self._store = MemoryStore(bootstrap.resolve_memory_path())
        return getattr(self._store, name)


memory: MemoryStore | _LazyMemory = _LazyMemory()


NEXT_ACTIONS = {
    "source_unavailable": (
        "Retry this tool later; if it keeps failing, tell the user the source is "
        "unavailable and do not invent values."
    ),
    "unexpected_format": (
        "The source changed its format: tell the user and do not use numbers "
        "from this response."
    ),
}


def source_error_payload(exc: wallet_client.SourceError) -> dict:
    """Convert a data-source failure into the structured error envelope."""
    payload = exc.to_payload()
    hint = NEXT_ACTIONS.get(exc.code)
    if hint:
        payload["error"]["message"] = f"{exc.message} {hint}"
    return payload


def memory_error_payload(exc: MemoryUnavailableError) -> dict:
    """Convert a memory-store failure into the structured error envelope.

    The agent should inform the user and keep operating without memory
    (corrupted memory must not disable the other tools).
    """
    return {"error": {"code": exc.code, "message": str(exc)}}


def _memory_or_param_error(exc: Exception) -> dict:
    if isinstance(exc, MemoryUnavailableError):
        return memory_error_payload(exc)
    if isinstance(exc, StateConflictError):
        return {"error": {"code": exc.code, "message": str(exc)}}
    return {"error": {"code": "invalid_params", "message": str(exc)}}


def _not_found(what: str) -> dict:
    return {"error": {"code": "not_found", "message": what}}


MEMORY_ERRORS = (MemoryUnavailableError, StateConflictError, ValueError)


@mcp.tool
async def get_wallet_summary() -> dict:
    """Overview of the configured wallet: applied amount, patrimony (equity),
    variation, and total and 12-month returns.

    Use this first when the user asks "how is my wallet doing?". The response is
    a data envelope: always tell the user the data freshness by mentioning
    `fetched_at` and whether the answer came from the in-memory cache
    (`cached=true`). On failure this returns {"error": {"code", "message"}} —
    never invent values.

    When the envelope has `privacy.masked` true, the operator withheld monetary
    amounts and quantities: work with the percentages and ratios provided and
    never estimate or reconstruct the withheld values.
    """
    try:
        envelope = await wallet_client.wallet_client.get_summary()
        return privacy.mask("summary", envelope)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_wallet_allocation() -> dict:
    """Wallet allocation broken down by asset (ticker) and by asset class.

    Use together with get_wallet_positions to analyze rebalancing:
    compare each position's percent_wallet against its percent_ideal, order the
    deviations by magnitude (0.1 percentage-point precision), and when
    suggesting new contributions prioritize assets below their ideal percent
    that carry a positive `buy` flag from the source. Never suggest selling an
    asset unless the user explicitly asks for it; if the wallet is aligned with
    the ideal, say so instead of forcing suggestions. This is also a data
    envelope — always mention `fetched_at` and `cached` when presenting the
    numbers.

    When the envelope has `privacy.masked` true, the operator withheld monetary
    amounts and quantities: work with the percentages and ratios provided and
    never estimate or reconstruct the withheld values.
    """
    try:
        envelope = await wallet_client.wallet_client.get_allocation()
        return privacy.mask("allocation", envelope)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_wallet_positions(asset_type: str) -> dict:
    """Detailed positions of one asset class of the wallet.

    When the envelope has `privacy.masked` true, the operator withheld monetary
    amounts and quantities: work with the percentages and ratios provided and
    never estimate or reconstruct the withheld values.

    Each position includes quantity, average price, current quote, equity,
    profitability, percent of wallet (percent_wallet), ideal percent
    (percent_ideal), fundamental indicators when the class provides them
    (P/E, P/B, dividend yield, ROE) and the source's buy flag. Positions are
    in data.data; a class with no positions has data.data=[] (not an error). Never invent
    indicator values that the source did not provide. When data.truncated is
    true the source stopped returning new rows before its declared total: tell
    the user the list is incomplete and do not present it as the whole class.

    Presentation rules: compare percent_wallet vs percent_ideal when discussing
    rebalancing; for EtfInternational positions, remind the user that equity
    involves currency conversion; always mention `cached` and `fetched_at`.

    For on-demand asset REPORTS: start from the position data here,
    add the current quote via get_asset_quote, then enrich with recent events
    from your own web search, citing every source; if no relevant recent news
    exists, say so explicitly instead of padding with generic content.

    Args:
        asset_type: One of Ticker (Brazilian stocks), Fii (real estate funds),
            EtfInternational (international ETFs), Treasure (Brazilian treasury
            bonds), Crypto. Any case is accepted; other values return an
            invalid_asset_type error listing the valid types.
    """
    try:
        envelope = await wallet_client.wallet_client.get_positions(asset_type)
        return privacy.mask("positions", envelope)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_asset_quote(ticker: str) -> dict:
    """Current market quote and fundamentals of a ticker (any asset, in the
    wallet or not): price, day and 12-month variation, Graham and Bazin fair
    prices, P/E, P/BV, dividend yield and sector.

    IMPORTANT presentation rules: quotes from the B3 have an inherent delay of
    ~15 minutes — always state this when giving prices. Always mention
    `cached`/`fetched_at` (the response is a data envelope). When the ticker is
    also in the wallet, cross the quote with the position's average price using
    get_wallet_positions. Unknown tickers return a ticker_not_found error with
    guidance to check spelling — never guess another ticker. Non-B3 assets (FIIs,
    international ETFs, crypto, treasury) return asset_type_not_supported.

    For on-demand asset REPORTS: combine this quote and the wallet
    position (when held) with recent events found through your own web search,
    citing every source; if no relevant recent news exists, say so explicitly
    instead of padding the report with generic content.

    Args:
        ticker: Asset ticker (e.g. PETR4, MXRF11, IVVB11). Any case accepted.
    """
    try:
        return await wallet_client.rest_client.get_quote(ticker)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_earnings(
    start_date: str | None = None, end_date: str | None = None
) -> dict:
    """Earnings (dividends, interest, income) received by the wallet in a period.

    When the operator enabled privacy mode this tool returns a
    privacy_mode_unavailable error: say so and do not estimate earnings.

    Presentation rules: present the total (data.sum) for exactly the requested
    window; this endpoint does not include per-asset earnings. A period without
    earnings is not an error — state it plainly. Always mention
    `cached`/`fetched_at`.

    Args:
        start_date: YYYY-MM-DD. Omit both dates to get the last 12 months.
        end_date: YYYY-MM-DD. Must be after start_date — an inverted range
            returns an invalid_params error (never a silent empty result).
    """
    try:
        if privacy.enabled():
            wallet_client.wallet_client.resolve_earnings_period(start_date, end_date)
            return privacy.unavailable_error("get_earnings")
        return await wallet_client.wallet_client.get_earnings(start_date, end_date)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def get_patrimony_history(months: int) -> dict:
    """Monthly patrimony evolution over a horizon, separating contributions
    from capital gains.

    When the operator enabled privacy mode this tool returns a
    privacy_mode_unavailable error: say so and do not estimate the series.

    Presentation rules: show the monthly series splitting what was contributed
    from what the market added; when the user asks "how did my patrimony
    evolve", propose a horizon if none was given. Always mention
    `cached`/`fetched_at`.

    Args:
        months: Integer horizon from 1 to 600 (e.g. 12, 24, 60).
    """
    try:
        # Arguments first: a bad horizon is invalid_params even in privacy mode.
        wallet_client.check_months(months)
        if privacy.enabled():
            return privacy.unavailable_error("get_patrimony_history")
        return await wallet_client.wallet_client.get_patrimony_history(months)
    except wallet_client.SourceError as exc:
        return source_error_payload(exc)


@mcp.tool
async def create_price_alert(ticker: str, direction: str, limit_price: float) -> dict:
    """Register a price alert for an asset. The alert is evaluated at the start
    of the NEXT session by get_session_context — there is no continuous
    monitoring outside sessions (scope of this product).

    Note: quotes only exist for B3 stocks; alerts on other asset classes stay
    active but are reported as pending check (asset_type_not_supported).

    Args:
        ticker: Asset ticker (uppercase-normalized).
        direction: 'above' (notify when price >= limit) or 'below'
            (notify when price <= limit). Boundaries are inclusive.
        limit_price: Price threshold, must be greater than zero.
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
        return _not_found(
            f"Price alert {alert_id} not found. Use list_price_alerts to see the valid ids."
        )
    return cancelled


def _parse_quote_price(data) -> float | None:
    """Extract the current price from a quote payload, or None when unavailable."""
    try:
        raw = data["variation_day"]["last_quotation"]
        if isinstance(raw, bool):
            return None
        if isinstance(raw, (int, float)):
            price = float(raw)
        else:
            price = float(str(raw).replace(",", "."))
        return price if math.isfinite(price) and price > 0 else None
    except (KeyError, TypeError, ValueError, OverflowError):
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
    active; so are alerts whose only quote is stale cached data served during
    a source outage (reason "stale_quote"), because a trigger is terminal and
    must never fire on an old price. Use `pending_decisions` to follow up on earlier recommendations and
    `recent_insights` to never repeat an alert as if it were new.

    `memory_status` is "ok", "unavailable" or "read_only". If it is
    "unavailable", tell the user memory could not be loaded and keep operating
    without it. If it is "read_only", the memory is readable but cannot be
    written (alerts are not evaluated): tell the user and do not attempt to
    save anything. A memory_busy error means another client is writing: retry
    this tool call.
    """
    try:
        digest = memory.session_digest()
    except MemoryBusyError as exc:
        return memory_error_payload(exc)
    except MemoryUnavailableError:
        return _session_context(None, [], [], "unavailable")
    try:
        active_alerts = memory.list_price_alerts("active")
    except MemoryBusyError as exc:
        return memory_error_payload(exc)
    except MemoryUnavailableError:
        return _session_context(digest, [], [], "unavailable")

    if memory.read_only:
        return _session_context(digest, [], [], "read_only")

    quotes: dict = {}
    pending_check: list = []
    attempted: set[str] = set()
    for alert in active_alerts:
        if not memory_store.alert_is_valid(alert):
            pending_check.append(
                {"alert_id": alert.get("id"), "reason": "invalid_alert"}
            )
            continue
        ticker = alert["ticker"].strip().upper()
        if ticker in attempted:
            continue
        attempted.add(ticker)
        try:
            envelope = await wallet_client.rest_client.get_quote(ticker)
            if wallet_client.rest_client.is_stale(envelope):
                # Never fire a terminal alert on an old price.
                pending_check.append({"ticker": ticker, "reason": "stale_quote"})
                continue
            price = _parse_quote_price(envelope.get("data"))
            if price is None:
                pending_check.append({"ticker": ticker, "reason": "unexpected_format"})
            else:
                quotes[ticker] = price
        except wallet_client.SourceError as exc:
            pending_check.append({"ticker": ticker, "reason": exc.code})

    try:
        triggered = memory.evaluate_alerts(quotes)
    except MemoryBusyError as exc:
        return memory_error_payload(exc)
    except MemoryReadOnlyError:
        return _session_context(digest, [], pending_check, "read_only")
    except MemoryUnavailableError:
        return _session_context(digest, [], pending_check, "unavailable")
    return _session_context(digest, triggered, pending_check, "ok")


def _session_context(digest, triggered: list, pending_check: list, status: str) -> dict:
    return {
        "memory": digest,
        "triggered_alerts": triggered,
        "pending_check": pending_check,
        "memory_status": status,
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
async def record_decision_outcome(
    decision_id: int, outcome: str, note: str | None = None
) -> dict:
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
        return _not_found(
            f"Decision {decision_id} not found. Use get_session_context (pending_decisions) to see the valid ids."
        )
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


def main() -> None:
    """Run the server, or the install assistant when argv starts with 'install'."""
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        from .installer import cli

        raise SystemExit(cli.run(sys.argv[2:]))
    global memory
    config = bootstrap.load_config()
    wallet_client.configure(config)
    privacy.configure(config)
    if privacy.enabled():
        bootstrap.warn(bootstrap.MASK_ACTIVE_MESSAGE)
    memory = MemoryStore(bootstrap.resolve_memory_path())
    asyncio.run(wallet_client.validate_wallet(wallet_client.WALLET_ID))
    mcp.run()


if __name__ == "__main__":
    main()
