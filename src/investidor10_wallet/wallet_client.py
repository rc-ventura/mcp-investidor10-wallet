import datetime
import json
import math
import os
import re
import time

import httpx

from . import bootstrap

WALLET_PROXY_BASE_URL = "https://investidor10.com.br/wallet/api/proxy/wallet-app"
REST_BASE_URL = "https://investidor10.com.br/api/rest"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    )
}


WALLET_ID = os.getenv("WALLET_ID", "").strip()
CACHE_TTL_SECONDS = 600.0
MAX_STALE_SECONDS = 86400.0
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_CACHE_ENTRIES = 256
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_POSITION_PAGES = 400
MAX_HISTORY_MONTHS = 600


def _now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()


def _matches(value, typ) -> bool:
    """Type check for source payload fields; bools never count as numbers."""
    if isinstance(value, bool) and typ in (int, float, (int, float)):
        return False
    return isinstance(value, typ)


# The live summary endpoint returns numeric strings (e.g. "96801.5575437"):
NUMERIC = "numeric"


def _is_numeric(value) -> bool:
    """True for int/float (bools excluded) or a numeric string, finite."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, str):
        try:
            number = float(value.replace(",", "."))
        except (ValueError, OverflowError):
            return False
        return math.isfinite(number)
    return False


class SourceError(Exception):
    """Structured failure of the Investidor10 data source.

    Codes: source_unavailable (down/timeout), unexpected_format (schema drift).
    """

    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


async def _read_capped(response: httpx.Response, path: str) -> bytes:
    """Read a streamed body, refusing one larger than MAX_RESPONSE_BYTES."""
    too_large = SourceError(
        "unexpected_format",
        f"Investidor10 API response for {path} is larger than "
        f"{MAX_RESPONSE_BYTES} bytes — refusing to read it",
    )
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
        raise too_large
    chunks = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise too_large
        chunks.append(chunk)
    return b"".join(chunks)


VALID_ASSET_TYPES = ("Ticker", "Fii", "EtfInternational", "Treasure", "Crypto")

ASSET_TYPE_ALIASES = {
    "ticker": "Ticker",
    "fii": "Fii",
    "etfinternational": "EtfInternational",
    "treasure": "Treasure",
    "crypto": "Crypto",
}


def normalize_asset_type(asset_type: str) -> str:
    """Map a user-supplied asset type (any case, trimmed) to the API value."""
    if not isinstance(asset_type, str):
        raise SourceError(
            "invalid_asset_type",
            f"Invalid asset type. Valid types: {', '.join(VALID_ASSET_TYPES)}",
        )
    canonical = ASSET_TYPE_ALIASES.get(asset_type.strip().lower())
    if canonical is None:
        raise SourceError(
            "invalid_asset_type",
            f"Invalid asset type '{asset_type}'. Valid types: {', '.join(VALID_ASSET_TYPES)}",
        )
    return canonical


class WalletClient:
    """HTTP client with an in-process TTL cache keyed by path + params."""

    def __init__(
        self,
        base_url: str,
        wallet_id: str | None = None,
        ttl_seconds: float | None = None,
        headers: dict | None = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        max_stale_seconds: float | None = None,
        *,
        _allow_unconfigured: bool = False,
    ):
        if wallet_id is None:
            wallet_id = WALLET_ID
        if ttl_seconds is None:
            ttl_seconds = CACHE_TTL_SECONDS
        if max_stale_seconds is None:
            max_stale_seconds = MAX_STALE_SECONDS
        self.base_url = base_url.rstrip("/")
        self.wallet_id = str(wallet_id)
        if not _allow_unconfigured and not re.fullmatch(r"[0-9]+", self.wallet_id):
            raise SourceError("invalid_params", "WALLET_ID must be numeric")
        self.ttl_seconds = ttl_seconds
        self.max_stale_seconds = max_stale_seconds
        self.headers = {**BROWSER_HEADERS, **(headers or {})}
        self.timeout = timeout
        # cache_key -> (monotonic_timestamp, fetched_at_iso, payload)
        self._cache: dict[tuple, tuple[float, str, object]] = {}

    @staticmethod
    def _envelope(data, cached: bool, fetched_at: str) -> dict:
        return {"cached": cached, "fetched_at": fetched_at, "data": data}

    def is_stale(self, envelope: dict) -> bool:
        """True for an expired cache entry served during a source outage.

        The age comes from this client's own cache entry, on the same
        monotonic clock that request() uses to decide TTL and stale serving,
        so a wall-clock step can never make old data look fresh. A regular
        cache hit (younger than the TTL) is fresh. A cached envelope whose
        entry is no longer in this cache has unknown age and counts as stale.
        The entry is matched by `data` identity, so pass the envelope exactly as
        request() returned it: a copied or masked `data` also counts as stale.
        Callers that make terminal decisions (alert triggers) must skip it.
        """
        if not envelope.get("cached"):
            return False
        for cached_at, fetched_at, data in self._cache.values():
            if data is envelope.get("data") and fetched_at == envelope.get(
                "fetched_at"
            ):
                return time.monotonic() - cached_at >= self.ttl_seconds
        return True

    def _stale_envelope(self, hit, path: str) -> dict:
        """Serve an expired cache entry on outage only while it is still recent.

        The age bound (WALLET_CACHE_MAX_STALE_SECONDS, default 24h) keeps the
        5xx/transport fallback within "recent cached data": older entries fail
        explicitly instead of presenting arbitrarily old financial data.
        """
        cached_at, fetched_at, data = hit
        age = time.monotonic() - cached_at
        if age <= self.max_stale_seconds:
            return self._envelope(data, cached=True, fetched_at=fetched_at)
        raise SourceError(
            "source_unavailable",
            f"Investidor10 API request failed for {path} and the cached data is {age:.0f}s old, "
            f"older than the max stale age of {self.max_stale_seconds:.0f}s — refusing to serve it",
        )

    async def request(
        self,
        path: str,
        params: dict | None = None,
        required_keys=None,
        expected_type: type | None = None,
        required_types: dict | None = None,
    ) -> dict:
        """GET base_url + path with TTL cache; returns the data envelope.

        Failures never fabricate values: wrong shapes raise `unexpected_format`
        before anything is cached, and a temporary source outage (HTTP 5xx or
        transport error) serves the stale cache with its explicit age while it
        is within the max-stale bound; an older entry fails explicitly.
        """
        cache_key = (self.base_url, path, tuple(sorted((params or {}).items())))
        hit = self._cache.get(cache_key)
        now = time.monotonic()
        if hit and now - hit[0] < self.ttl_seconds:
            return self._envelope(hit[2], cached=True, fetched_at=hit[1])

        try:
            async with (
                httpx.AsyncClient(
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=False,
                ) as client,
                client.stream(
                    "GET", f"{self.base_url}{path}", params=params
                ) as response,
            ):
                status = response.status_code
                body = await _read_capped(response, path) if status < 400 else b""
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            if hit:
                return self._stale_envelope(hit, path)
            raise SourceError(
                "source_unavailable", f"Investidor10 API request failed: {exc}"
            ) from exc

        if status >= 500 and hit:
            return self._stale_envelope(hit, path)
        if status >= 400:
            message = f"Investidor10 API returned HTTP {status} for {path}"
            if 400 <= status < 500 and self.base_url == WALLET_PROXY_BASE_URL:
                message += " — check WALLET_ID"
            raise SourceError(
                "source_unavailable",
                message,
                status_code=status,
            )

        try:
            data = json.loads(body)
        except ValueError as exc:
            raise SourceError(
                "unexpected_format",
                f"Investidor10 API returned non-JSON body for {path}",
            ) from exc

        if expected_type is not None and not isinstance(data, expected_type):
            raise SourceError(
                "unexpected_format",
                f"Investidor10 API payload for {path} has an unexpected type",
            )
        if required_keys is not None:
            missing = [
                key
                for key in required_keys
                if not isinstance(data, dict) or key not in data
            ]
            if missing:
                raise SourceError(
                    "unexpected_format",
                    f"Investidor10 API payload for {path} is missing keys: {missing}",
                )
        if required_types is not None:
            for key, typ in required_types.items():
                value = data.get(key) if isinstance(data, dict) else None
                ok = _is_numeric(value) if typ is NUMERIC else _matches(value, typ)
                if not ok:
                    raise SourceError(
                        "unexpected_format",
                        f"Investidor10 API payload for {path} field {key} has an unexpected type",
                    )

        fetched_at = _now_iso()
        self._remember(cache_key, fetched_at, data)
        return self._envelope(data, cached=False, fetched_at=fetched_at)

    def _remember(self, cache_key: tuple, fetched_at: str, data) -> None:
        """Cache a payload, keeping the cache bounded.

        Entries too old to be served even as stale are dropped, then the
        oldest ones beyond MAX_CACHE_ENTRIES (dicts keep insertion order).
        """
        now = time.monotonic()
        for key in [
            key
            for key, (cached_at, _, _) in self._cache.items()
            if now - cached_at > self.max_stale_seconds
        ]:
            del self._cache[key]
        self._cache.pop(cache_key, None)
        self._cache[cache_key] = (now, fetched_at, data)
        while len(self._cache) > MAX_CACHE_ENTRIES:
            del self._cache[next(iter(self._cache))]

    async def get_summary(self) -> dict:
        """Wallet summary: applied amount, equity, variations, total/12M returns.

        The live source returns applied/equity as numeric strings, so they are
        validated as NUMERIC (finite number or numeric string), never cached
        when present-but-invalid.
        """
        return await self.request(
            f"/summary/metrics/{self.wallet_id}",
            params={"type": "without-earnings", "raw": 1},
            required_keys=("applied", "equity"),
            required_types={"applied": NUMERIC, "equity": NUMERIC},
        )

    async def get_allocation(self) -> dict:
        """Wallet allocation by asset and asset class."""
        return await self.request(
            f"/summary/donutchart/{self.wallet_id}/all",
            params={"groupBy": "ticker"},
            expected_type=list,
        )

    async def get_positions(self, asset_type: str) -> dict:
        """Detailed positions of one asset class, paginated until the source total.

        The source returns at most 50 rows per page; the client walks pages
        (start += collected rows) until every position of the class is
        collected, so the 100%-of-assets criterion holds for classes larger
        than one page. The merge is guarded: rows are deduplicated by ticker
        (full-row identity as fallback), the loop stops on a page that adds no
        new rows, and `total` in the merged payload reflects the unique rows
        actually collected — never more than `data` contains. The merged
        payload keeps the source shape {total, data, weighted, draw} plus
        `truncated`, true when collection stopped below the declared total or
        hit the MAX_POSITION_PAGES hard stop. A declared total that is not a
        positive int, or that the collected rows exceed, is treated as absent.
        """
        canonical = normalize_asset_type(asset_type)
        page_size = 50
        rows: list = []
        seen: set = set()
        envelope = None
        page = None
        total = None
        pages = 0
        capped = False
        while True:
            if pages >= MAX_POSITION_PAGES:
                capped = True
                break
            pages += 1
            start = len(rows)
            envelope = await self.request(
                f"/summary/actives/{self.wallet_id}/{canonical}",
                params={
                    "raw": 1,
                    "api_version": "v2",
                    "start": start,
                    "length": page_size,
                    "order_column": "equity_total",
                    "order_dir": "desc",
                },
                required_keys=("data",),
                required_types={"data": list},
            )
            page = envelope["data"]
            declared = page.get("total")
            if type(declared) is int and declared > 0:
                total = declared if total is None else max(total, declared)
            added = 0
            for row in page["data"]:
                ticker = row.get("ticker") if isinstance(row, dict) else None
                identity = (
                    f"ticker:{ticker}"
                    if ticker
                    else json.dumps(row, sort_keys=True, default=str)
                )
                if identity not in seen:
                    seen.add(identity)
                    rows.append(row)
                    added += 1
            if total is not None and len(rows) > total:
                total = None
            if (
                added == 0
                or len(page["data"]) < page_size
                or (total is not None and len(rows) >= total)
            ):
                break
        merged = dict(page)
        merged["data"] = rows
        merged["total"] = len(rows)
        merged["truncated"] = capped or (total is not None and len(rows) < total)
        return {**envelope, "data": merged}

    async def get_quote(self, ticker: str) -> dict:
        """Market quote and fundamentals of one ticker (REST assets API).

        This endpoint only covers B3 stocks: FIIs, international ETFs, crypto
        and treasury return HTTP 410 and map to asset_type_not_supported — not
        to ticker_not_found.
        """
        if not isinstance(ticker, str):
            raise SourceError("invalid_params", "ticker must be a valid ticker string")
        normalized = ticker.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9]{3,11}", normalized):
            raise SourceError(
                "invalid_params",
                "ticker must be 4-12 letters or digits, starting with a letter",
            )
        try:
            envelope = await self.request(f"/assets/tickers/{normalized}")
        except SourceError as exc:
            if exc.status_code == 404:
                raise SourceError(
                    "ticker_not_found",
                    f"Ticker '{normalized}' was not found — check the spelling",
                ) from exc
            if exc.status_code == 410:
                raise SourceError(
                    "asset_type_not_supported",
                    f"Quotes for '{normalized}' are not available on this source: the Investidor10 "
                    "REST assets API only covers B3 stocks (FIIs, international ETFs, crypto and "
                    "treasury are not supported). Use get_wallet_positions for wallet-held assets.",
                ) from exc
            raise
        data = envelope["data"]
        if isinstance(data, dict) and not data:
            raise SourceError(
                "ticker_not_found",
                f"Ticker '{normalized}' was not found — check the spelling",
            )
        if not isinstance(data, dict):
            raise SourceError(
                "unexpected_format",
                f"Investidor10 API payload for /assets/tickers/{normalized} has an unexpected type",
            )
        if "variation_day" not in data:
            raise SourceError(
                "unexpected_format",
                f"Investidor10 API payload for /assets/tickers/{normalized} is missing keys: variation_day",
            )
        try:
            raw = data["variation_day"]["last_quotation"]
            if isinstance(raw, bool):
                raise ValueError
            price = float(str(raw).replace(",", "."))
            if not math.isfinite(price) or price <= 0:
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            raise SourceError(
                "unexpected_format",
                f"Investidor10 API returned an invalid quote for {normalized}",
            ) from None
        return envelope

    @staticmethod
    def resolve_earnings_period(
        start_date: str | None = None, end_date: str | None = None
    ) -> tuple[str, str]:
        """Resolve and validate the earnings window; defaults to the last 12 months."""
        if start_date is None and end_date is None:
            today = datetime.date.today()
            try:
                start_date = today.replace(year=today.year - 1).isoformat()
            except ValueError:
                start_date = today.replace(year=today.year - 1, day=28).isoformat()
            end_date = today.isoformat()
        else:
            start_date = WalletClient._validate_date(start_date, "start_date")
            end_date = WalletClient._validate_date(end_date, "end_date")
        if start_date > end_date:
            raise SourceError(
                "invalid_params",
                f"start_date ({start_date}) must not be after end_date ({end_date}) — check the dates",
            )
        return start_date, end_date

    async def get_earnings(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict:
        """Earnings received in a period; defaults to the last 12 months."""
        start_date, end_date = self.resolve_earnings_period(start_date, end_date)
        return await self.request(
            f"/earnings/total-period/{self.wallet_id}",
            params={"start_date": start_date, "end_date": end_date},
            required_keys=("sum",),
            required_types={"sum": (int, float)},
        )

    @staticmethod
    def _validate_date(value: str | None, field: str) -> str:
        if value is None:
            raise SourceError(
                "invalid_params", f"{field} is required when the other date is provided"
            )
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
        ):
            raise SourceError(
                "invalid_params", f"{field} must be in YYYY-MM-DD format, got '{value}'"
            )
        try:
            return datetime.date.fromisoformat(value).isoformat()
        except ValueError:
            raise SourceError(
                "invalid_params", f"{field} must be in YYYY-MM-DD format, got '{value}'"
            ) from None

    async def get_patrimony_history(self, months: int) -> dict:
        """Monthly patrimony evolution (contributions vs capital gains)."""
        check_months(months)
        return await self.request(
            f"/summary/barchart/{self.wallet_id}/{months}/all", expected_type=list
        )


def check_months(months) -> None:
    """Validate the patrimony-history horizon (a positive integer, capped)."""
    if type(months) is not int or not 0 < months <= MAX_HISTORY_MONTHS:
        raise SourceError(
            "invalid_params",
            f"months must be an integer from 1 to {MAX_HISTORY_MONTHS} "
            f"(e.g. 12, 24, 60), got {months!r}",
        )


wallet_client = WalletClient(WALLET_PROXY_BASE_URL, _allow_unconfigured=True)
rest_client = WalletClient(REST_BASE_URL, _allow_unconfigured=True)


def configure(config: dict) -> None:
    """Apply validated bootstrap configuration to module-level singletons."""
    global WALLET_ID, CACHE_TTL_SECONDS, MAX_STALE_SECONDS
    WALLET_ID = config["wallet_id"]
    CACHE_TTL_SECONDS = config["ttl_seconds"]
    MAX_STALE_SECONDS = config["max_stale_seconds"]
    for client in (wallet_client, rest_client):
        client.wallet_id = WALLET_ID
        client.ttl_seconds = CACHE_TTL_SECONDS
        client.max_stale_seconds = MAX_STALE_SECONDS


async def validate_wallet(
    wallet_id: str, base_url: str = WALLET_PROXY_BASE_URL, timeout: float = 10.0
) -> None:
    """Probe the configured wallet once at startup.

    Aborts with PT-BR guidance when the wallet is missing or private; on a
    source outage the server warns and keeps starting, so a temporary failure
    never blocks local operation.
    """
    try:
        async with (
            httpx.AsyncClient(
                headers=BROWSER_HEADERS,
                timeout=timeout,
                follow_redirects=False,
            ) as client,
            client.stream("GET", f"{base_url}/summary/metrics/{wallet_id}") as response,
        ):
            status = response.status_code
    except (httpx.HTTPError, httpx.InvalidURL):
        bootstrap.warn(bootstrap.PROBE_UNAVAILABLE_MESSAGE.format(wallet_id=wallet_id))
        return
    if status == 200:
        return
    if status == 404:
        bootstrap.fail(bootstrap.WALLET_NOT_FOUND_MESSAGE.format(wallet_id=wallet_id))
    if status in (401, 403):
        bootstrap.fail(bootstrap.WALLET_PRIVATE_MESSAGE.format(wallet_id=wallet_id))
    bootstrap.warn(bootstrap.PROBE_UNAVAILABLE_MESSAGE.format(wallet_id=wallet_id))
