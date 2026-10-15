"""Async HTTP client for the Investidor10 wallet API with TTL caching.

Wraps the two public (no-auth) API surfaces of investidor10.com.br:
  - wallet proxy: https://investidor10.com.br/wallet/api/proxy/wallet-app
  - REST assets: https://investidor10.com.br/api/rest

Every successful request returns a data envelope:
    {"cached": bool, "fetched_at": "<ISO-8601>", "data": <payload>}
so the agent can always tell the user how fresh the data is (FR-014).

All failures raise SourceError with a structured code; callers must convert
it into {"error": {"code", "message"}} and never fabricate values (FR-016).
"""

import datetime
import os
import time

import httpx

WALLET_PROXY_BASE_URL = "https://investidor10.com.br/wallet/api/proxy/wallet-app"
REST_BASE_URL = "https://investidor10.com.br/api/rest"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    )
}

WALLET_ID = os.getenv("WALLET_ID", "2061045")
CACHE_TTL_SECONDS = float(os.getenv("WALLET_CACHE_TTL_SECONDS", "600"))
REQUEST_TIMEOUT_SECONDS = 20.0


def _now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()


class SourceError(Exception):
    """Structured failure of the Investidor10 data source.

    Codes: source_unavailable (down/timeout), unexpected_format (schema drift).
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


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
        wallet_id: str = WALLET_ID,
        ttl_seconds: float = CACHE_TTL_SECONDS,
        headers: dict | None = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.wallet_id = wallet_id
        self.ttl_seconds = ttl_seconds
        self.headers = {**BROWSER_HEADERS, **(headers or {})}
        self.timeout = timeout
        # cache_key -> (monotonic_timestamp, fetched_at_iso, payload)
        self._cache: dict[tuple, tuple[float, str, object]] = {}

    @staticmethod
    def _envelope(data, cached: bool, fetched_at: str) -> dict:
        return {"cached": cached, "fetched_at": fetched_at, "data": data}

    async def request(self, path: str, params: dict | None = None, required_keys=None) -> dict:
        """GET base_url + path with TTL cache; returns the data envelope."""
        cache_key = (self.base_url, path, tuple(sorted((params or {}).items())))
        hit = self._cache.get(cache_key)
        now = time.monotonic()
        if hit and now - hit[0] < self.ttl_seconds:
            return self._envelope(hit[2], cached=True, fetched_at=hit[1])

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            # Source failure: serve the stale cache (with its explicit age)
            # rather than failing outright; otherwise fail explicitly.
            if hit:
                return self._envelope(hit[2], cached=True, fetched_at=hit[1])
            raise SourceError("source_unavailable", f"Investidor10 API request failed: {exc}") from exc

        if response.status_code >= 400:
            raise SourceError(
                "source_unavailable", f"Investidor10 API returned HTTP {response.status_code} for {path}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise SourceError("unexpected_format", f"Investidor10 API returned non-JSON body for {path}") from exc

        if required_keys is not None:
            missing = [key for key in required_keys if key not in data]
            if missing:
                raise SourceError(
                    "unexpected_format", f"Investidor10 API payload for {path} is missing keys: {missing}"
                )

        fetched_at = _now_iso()
        self._cache[cache_key] = (time.monotonic(), fetched_at, data)
        return self._envelope(data, cached=False, fetched_at=fetched_at)

    # ------------------------------------------------------------- wallet endpoints

    async def get_summary(self) -> dict:
        """Wallet summary: applied amount, equity, variations, total/12M returns."""
        return await self.request(
            f"/summary/metrics/{self.wallet_id}", params={"type": "without-earnings", "raw": 1}
        )

    async def get_allocation(self) -> dict:
        """Wallet allocation by asset and asset class."""
        return await self.request(f"/summary/donutchart/{self.wallet_id}/all", params={"groupBy": "ticker"})

    async def get_positions(self, asset_type: str) -> dict:
        """Detailed positions of one asset class (see VALID_ASSET_TYPES)."""
        canonical = normalize_asset_type(asset_type)
        return await self.request(
            f"/summary/actives/{self.wallet_id}/{canonical}",
            params={
                "raw": 1,
                "api_version": "v2",
                "start": 0,
                "length": 50,
                "order_column": "equity_total",
                "order_dir": "desc",
            },
        )


wallet_client = WalletClient(WALLET_PROXY_BASE_URL)
rest_client = WalletClient(REST_BASE_URL)
