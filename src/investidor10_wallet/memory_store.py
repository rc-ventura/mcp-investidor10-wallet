import datetime
import json
import math
import os
import re
import tempfile

SCHEMA_VERSION = 1
COLLECTIONS = ("theses", "rules", "decisions", "insights_log", "alerts")

DECISION_KINDS = ("recommendation", "user_decision")
DECISION_OUTCOMES = ("accepted", "rejected", "postponed")

ALERT_DIRECTIONS = ("above", "below")
ALERT_STATES = ("active", "triggered", "cancelled")

# Ticker validity check shared by create_price_alert and alert_is_valid:
# 4-12 letters or digits, starting with a letter, on the uppercase ticker.
TICKER_PATTERN = re.compile(r"[A-Z][A-Z0-9]{3,11}")


class MemoryUnavailableError(Exception):
    """Raised when the memory store is in degraded mode.

    Callers (MCP tools) convert this into {"error": {"code": "memory_unavailable", ...}}
    so the agent can inform the user and keep operating without memory.
    """


def _empty_store() -> dict:
    store = {"version": SCHEMA_VERSION, "wallet_goal": None}
    for collection in COLLECTIONS:
        store[collection] = []
    return store


def _valid_collection(entries) -> bool:
    """A persisted collection must be a list of dicts with unique int ids >= 1."""
    if not isinstance(entries, list):
        return False
    ids = []
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        entry_id = entry.get("id")
        if type(entry_id) is not int or entry_id < 1:
            return False
        ids.append(entry_id)
    return len(ids) == len(set(ids))


def alert_is_valid(alert: dict) -> bool:
    """True when a persisted alert has a usable ticker, direction and limit.

    Used by the session bootstrap (to report invalid alerts instead of raising)
    and by evaluate_alerts (to skip them). Never raises for oversized numbers.
    The ticker check uses the same pattern as create_price_alert, applied to
    the normalized ticker so hand-edited lowercase tickers stay valid.
    """
    ticker = alert.get("ticker")
    direction = alert.get("direction")
    limit = alert.get("limit_price")
    if not isinstance(ticker, str) or not TICKER_PATTERN.fullmatch(
        ticker.strip().upper()
    ):
        return False
    if direction not in ALERT_DIRECTIONS:
        return False
    if type(alert.get("id")) is not int:
        return False
    if isinstance(limit, bool) or not isinstance(limit, (int, float)):
        return False
    try:
        return math.isfinite(float(limit)) and float(limit) > 0
    except (OverflowError, ValueError):
        return False


class MemoryStore:
    """JSON-file backed memory store with atomic persistence and degraded mode."""

    def __init__(self, path: str):
        self.path = path
        self.available = True
        self.data: dict = _empty_store()
        self._load()

    # ------------------------------------------------------------------ load/save

    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
            json.dumps(loaded, allow_nan=False)
        except FileNotFoundError:
            # First run: create an empty v1 store on disk.
            try:
                self.save()
            except MemoryUnavailableError:
                pass
            return
        except (OSError, ValueError, UnicodeDecodeError):
            # Corrupted file: preserve the original as a .broken-<timestamp>
            # backup before anything else could overwrite it, then degrade.
            self._backup_corrupt_file()
            self.available = False
            return

        if (
            isinstance(loaded, dict)
            and type(loaded.get("version")) is int
            and loaded["version"] > SCHEMA_VERSION
        ):
            # Valid JSON, unknown schema version: refuse to interpret or
            # rewrite it. Keep the file untouched and degrade.
            self.available = False
            return
        if (
            not isinstance(loaded, dict)
            or type(loaded.get("version")) is not int
            or loaded["version"] != SCHEMA_VERSION
            or "wallet_goal" not in loaded
            or not isinstance(loaded.get("wallet_goal"), (dict, type(None)))
            or any(not _valid_collection(loaded.get(key)) for key in COLLECTIONS)
        ):
            self._backup_corrupt_file()
            self.available = False
            return
        self.data = loaded

    def _backup_corrupt_file(self) -> None:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = f"{self.path}.broken-{stamp}"
        try:
            with open(self.path, "rb") as src:
                content = src.read()
            fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as dst:
                dst.write(content)
        except OSError:
            # Backup is best-effort; degraded mode is still the safe outcome.
            pass

    def save(self) -> None:
        """Persist the store atomically using a private temporary file."""
        self._require_available()
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=os.path.dirname(os.path.abspath(self.path)),
                prefix=".memory-",
                delete=False,
            ) as f:
                tmp_path = f.name
                json.dump(self.data, f, ensure_ascii=False, indent=2, allow_nan=False)
            os.replace(tmp_path, self.path)
        except (OSError, ValueError) as exc:
            self.available = False
            raise MemoryUnavailableError(
                f"Memory store could not be saved at {self.path}: {exc}"
            ) from exc
        finally:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def now_iso() -> str:
        """Current local time as an ISO-8601 string with timezone offset."""
        return datetime.datetime.now().astimezone().isoformat()

    def _require_available(self) -> None:
        if not self.available:
            raise MemoryUnavailableError(
                f"Memory store is unavailable (inaccessible or invalid file at {self.path}). "
                "The original file was not overwritten."
            )

    def _collection(self, collection: str) -> list:
        if collection not in COLLECTIONS:
            raise ValueError(f"Unknown collection: {collection}")
        self._require_available()
        return self.data.setdefault(collection, [])

    def next_id(self, collection: str) -> int:
        entries = self._collection(collection)
        return max((entry.get("id", 0) for entry in entries), default=0) + 1

    # ------------------------------------------------------------------ CRUD (base)

    def add(self, collection: str, entry: dict) -> dict:
        self._require_available()
        entry["id"] = self.next_id(collection)
        entry.setdefault("created_at", self.now_iso())
        self._collection(collection).append(entry)
        self.save()
        return entry

    def get_all(self, collection: str) -> list:
        return list(self._collection(collection))

    def find(self, collection: str, entry_id: int) -> dict | None:
        for entry in self._collection(collection):
            if entry.get("id") == entry_id:
                return entry
        return None

    def update(self, collection: str, entry_id: int, changes: dict) -> dict | None:
        entry = self.find(collection, entry_id)
        if entry is None:
            return None
        entry.update(changes)
        self.save()
        return entry

    # ---------------------------------------------------------- domain operations

    @staticmethod
    def _clean_text(value: str, field: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field} must be text")
        text = value.strip()
        if not text:
            raise ValueError(f"{field} must not be empty")
        return text

    def get_wallet_goal(self) -> dict | None:
        self._require_available()
        return self.data.get("wallet_goal")

    def set_wallet_goal(self, text: str) -> dict:
        self._require_available()
        goal = {"text": self._clean_text(text, "text"), "updated_at": self.now_iso()}
        self.data["wallet_goal"] = goal
        self.save()
        return goal

    def save_thesis(self, ticker: str, text: str) -> dict:
        return self.add(
            "theses",
            {
                "ticker": self._clean_text(ticker, "ticker").upper(),
                "text": self._clean_text(text, "text"),
                "updated_at": self.now_iso(),
            },
        )

    def get_theses(self, ticker: str | None = None) -> list:
        theses = self.get_all("theses")
        if ticker is None:
            return theses
        normalized = self._clean_text(ticker, "ticker").upper()
        return [t for t in theses if t.get("ticker") == normalized]

    def save_rule(self, text: str) -> dict:
        return self.add("rules", {"text": self._clean_text(text, "text")})

    def get_rules(self) -> list:
        return self.get_all("rules")

    def log_decision(
        self,
        kind: str,
        content: str,
        ticker: str | None = None,
        rationale: str | None = None,
    ) -> dict:
        self._require_available()
        if kind not in DECISION_KINDS:
            raise ValueError(
                f"Invalid decision kind '{kind}'. Valid kinds: {', '.join(DECISION_KINDS)}"
            )
        entry = {"kind": kind, "content": self._clean_text(content, "content")}
        if ticker is not None:
            entry["ticker"] = self._clean_text(ticker, "ticker").upper()
        else:
            entry["ticker"] = None
        if rationale is not None and not isinstance(rationale, str):
            raise ValueError("rationale must be text")
        entry["rationale"] = (rationale or "").strip() or None
        entry["date"] = self.now_iso()[:10]
        entry["outcome"] = "pending"
        entry["outcome_note"] = None
        entry["outcome_at"] = None
        return self.add("decisions", entry)

    def record_decision_outcome(
        self, decision_id: int, outcome: str, note: str | None = None
    ) -> dict | None:
        self._require_available()
        if outcome not in DECISION_OUTCOMES:
            raise ValueError(
                f"Invalid outcome '{outcome}'. Valid outcomes: {', '.join(DECISION_OUTCOMES)}"
            )
        if note is not None and not isinstance(note, str):
            raise ValueError("note must be text")
        return self.update(
            "decisions",
            decision_id,
            {
                "outcome": outcome,
                "outcome_note": (note or "").strip() or None,
                "outcome_at": self.now_iso(),
            },
        )

    def log_insight(self, kind: str, fingerprint: str, summary: str) -> dict:
        """Log a communicated insight; dedupes by fingerprint.

        Returns {"already_logged": False, "entry": ...} for new insights or
        {"already_logged": True, "existing": ...} when the fingerprint exists —
        in that case nothing is appended.
        """
        self._require_available()
        fingerprint = self._clean_text(fingerprint, "fingerprint")
        for existing in self.get_all("insights_log"):
            if existing.get("fingerprint") == fingerprint:
                return {"already_logged": True, "existing": existing}
        entry = self.add(
            "insights_log",
            {
                "kind": self._clean_text(kind, "kind"),
                "fingerprint": fingerprint,
                "summary": self._clean_text(summary, "summary"),
                "date": self.now_iso()[:10],
            },
        )
        return {"already_logged": False, "entry": entry}

    # ---------------------------------------------------------------- price alerts

    def create_price_alert(self, ticker: str, direction: str, limit_price) -> dict:
        """Create an alert with state='active'."""
        self._require_available()
        if direction not in ALERT_DIRECTIONS:
            raise ValueError(
                f"Invalid direction '{direction}'. Valid directions: {', '.join(ALERT_DIRECTIONS)}"
            )
        try:
            if isinstance(limit_price, bool):
                raise ValueError
            price = float(limit_price)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("limit_price must be a number") from None
        if not math.isfinite(price) or price <= 0:
            raise ValueError("limit_price must be a finite number greater than zero")
        normalized_ticker = self._clean_text(ticker, "ticker").upper()
        if not TICKER_PATTERN.fullmatch(normalized_ticker):
            raise ValueError(
                "ticker must be 4-12 letters or digits, starting with a letter"
            )
        return self.add(
            "alerts",
            {
                "ticker": normalized_ticker,
                "direction": direction,
                "limit_price": price,
                "state": "active",
                "triggered_at": None,
                "triggered_price": None,
            },
        )

    def list_price_alerts(self, state: str | None = None) -> list:
        self._require_available()
        alerts = self.get_all("alerts")
        if state is None:
            return alerts
        if state not in ALERT_STATES:
            raise ValueError(
                f"Invalid state '{state}'. Valid states: {', '.join(ALERT_STATES)}"
            )
        return [a for a in alerts if a.get("state") == state]

    def cancel_price_alert(self, alert_id: int) -> dict | None:
        """Cancel an active alert (terminal). Returns None when not found."""
        self._require_available()
        alert = self.find("alerts", alert_id)
        if alert is None:
            return None
        if alert.get("state") != "active":
            raise ValueError(
                f"Alert {alert_id} is already {alert.get('state')} and cannot be cancelled"
            )
        return self.update("alerts", alert_id, {"state": "cancelled"})

    def evaluate_alerts(self, quotes: dict) -> list:
        """Evaluate all active alerts against current quotes (session open only).

        quotes maps ticker -> current price. Tickers absent from `quotes`
        (check failed) are skipped and stay active. Triggers are terminal:
        a triggered alert is persisted as 'triggered' and never fires again.
        All satisfied alerts are persisted in ONE atomic save, so a save
        failure leaves the file untouched and every alert still active for
        the next session — no partially delivered notification is possible.
        """
        self._require_available()
        triggered = []
        for alert in self.get_all("alerts"):
            if alert.get("state") != "active" or not alert_is_valid(alert):
                continue
            price = quotes.get(alert["ticker"].strip().upper())
            if price is None:
                continue
            limit = float(alert["limit_price"])
            hit = price <= limit if alert["direction"] == "below" else price >= limit
            if hit:
                alert.update(
                    {
                        "state": "triggered",
                        "triggered_at": self.now_iso(),
                        "triggered_price": price,
                    }
                )
                triggered.append(alert)
        if triggered:
            self.save()
        return triggered

    def session_digest(self, recent_insights_limit: int = 10) -> dict:
        """Digest of the investor memory for the session bootstrap."""
        self._require_available()
        theses_by_ticker: dict = {}
        for thesis in self.get_all("theses"):
            theses_by_ticker.setdefault(thesis.get("ticker"), []).append(thesis)
        return {
            "wallet_goal": self.data.get("wallet_goal"),
            "theses": theses_by_ticker,
            "rules": self.get_rules(),
            "pending_decisions": [
                d for d in self.get_all("decisions") if d.get("outcome") == "pending"
            ],
            "recent_insights": self.get_all("insights_log")[-recent_insights_limit:]
            if recent_insights_limit
            else [],
        }
