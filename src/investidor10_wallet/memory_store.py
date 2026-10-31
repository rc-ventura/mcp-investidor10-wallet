import copy
import datetime
import errno
import glob
import hashlib
import json
import math
import os
import re
import tempfile
import threading
import time
from contextlib import contextmanager

import filelock

from . import bootstrap

SCHEMA_VERSION = 1
COLLECTIONS = ("theses", "rules", "decisions", "insights_log", "alerts")

DECISION_KINDS = ("recommendation", "user_decision")
DECISION_OUTCOMES = ("accepted", "rejected", "postponed")

ALERT_DIRECTIONS = ("above", "below")
ALERT_STATES = ("active", "triggered", "cancelled")

LOCK_TIMEOUT_SECONDS = 5.0
REPLACE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8)
UNSUPPORTED_LOCK_ERRNOS = {
    getattr(errno, name) for name in ("ENOSYS", "EOPNOTSUPP") if hasattr(errno, name)
}
NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
BINARY = getattr(os, "O_BINARY", 0)
MAX_NESTING_DEPTH = 32

TICKER_PATTERN = re.compile(r"[A-Z][A-Z0-9]{3,11}")


class MemoryUnavailableError(Exception):
    """Raised when the memory store is in degraded mode.

    Callers (MCP tools) convert this into {"error": {"code": "memory_unavailable", ...}}
    so the agent can inform the user and keep operating without memory.
    """

    code = "memory_unavailable"


class MemoryBusyError(MemoryUnavailableError):
    code = "memory_busy"


class MemoryReadOnlyError(MemoryUnavailableError):
    code = "memory_read_only"


class StateConflictError(Exception):
    """Raised when an entry exists but its state forbids the operation
    (e.g. cancelling an alert that already triggered). Not an argument error."""

    code = "state_conflict"


def _empty_store() -> dict:
    store = {"version": SCHEMA_VERSION, "wallet_goal": None}
    for collection in COLLECTIONS:
        store[collection] = []
    return store


def _nests_deeper_than(value, limit: int) -> bool:
    """Iterative depth check: the file may nest deeper than any recursion limit."""
    stack = [(value, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict):
            children = node.values()
        elif isinstance(node, list):
            children = node
        else:
            continue
        if depth > limit:
            return True
        stack.extend((child, depth + 1) for child in children)
    return False


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

    def __init__(self, path: str, lock_timeout: float = LOCK_TIMEOUT_SECONDS):
        self.path = path
        self.available = True
        self.read_only = False
        self.data: dict = _empty_store()
        self._local = threading.local()
        self._thread_lock = threading.Lock()
        self._lock_timeout = lock_timeout
        self._seen_file = False
        self._lock = filelock.FileLock(
            f"{path}.lock",
            timeout=lock_timeout,
            mode=0o600,
            fallback_to_soft=False,
            thread_local=False,
        )
        try:
            with self._locked():
                pass
        except MemoryBusyError:
            pass
        except MemoryUnavailableError:
            self.available = False

    def _busy(self) -> MemoryBusyError:
        return MemoryBusyError(
            "Investor memory is locked by another server process (another client "
            "is writing). Retry the same tool call in a moment."
        )

    def _acquire(self) -> bool:
        if self.read_only:
            return False
        if not os.path.isdir(os.path.dirname(os.path.abspath(self.path))):
            raise MemoryUnavailableError(
                f"Memory store directory for {self.path} does not exist."
            )
        try:
            self._lock.acquire()
        except filelock.Timeout as exc:
            raise self._busy() from exc
        except OSError as exc:
            if exc.errno not in UNSUPPORTED_LOCK_ERRNOS:
                raise MemoryUnavailableError(
                    f"Memory lock file {self.path}.lock could not be used: {exc}. "
                    "Retry the same tool call in a moment."
                ) from exc
            self.read_only = True
            bootstrap.warn(bootstrap.LOCK_UNSUPPORTED_MESSAGE.format(path=self.path))
            return False
        self._tighten_by_path(f"{self.path}.lock")
        return True

    def _tighten_by_path(self, path: str) -> None:
        """Tighten a file this process has no fd for, without following a link."""
        try:
            fd = os.open(path, os.O_RDONLY | NO_FOLLOW)
        except OSError as exc:
            bootstrap.warn(
                bootstrap.TIGHTEN_FAILED_MESSAGE.format(path=path, cause=exc)
            )
            return
        try:
            self._tighten(path, fd)
        finally:
            os.close(fd)

    @staticmethod
    def _tighten(path: str, fd: int | None = None) -> None:
        """Restrict a sidecar file to 0600, through its fd when one is open
        (fchmod never follows a symlink swapped in after the open)."""
        try:
            if fd is not None and hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
            else:
                os.chmod(path, 0o600)
        except OSError as exc:
            bootstrap.warn(
                bootstrap.TIGHTEN_FAILED_MESSAGE.format(path=path, cause=exc)
            )

    @contextmanager
    def _locked(self, reload: bool = True):
        depth = getattr(self._local, "depth", 0)
        if depth:
            self._local.depth = depth + 1
            try:
                yield
            finally:
                self._local.depth = depth
            return
        if not self._thread_lock.acquire(timeout=self._lock_timeout):
            raise self._busy()
        try:
            held = self._acquire()
            self._local.depth = 1
            try:
                if reload:
                    self._reload()
                yield
            finally:
                self._local.depth = 0
                if held:
                    self._lock.release()
        finally:
            self._thread_lock.release()

    def _read_file(self) -> bytes:
        """Read the memory file by fd, never through a symlink."""
        fd = os.open(self.path, os.O_RDONLY | NO_FOLLOW | BINARY)
        with os.fdopen(fd, "rb") as f:
            return f.read()

    def _reload(self) -> None:
        content = None
        try:
            content = self._read_file()
            # Set before validating: a rejected file deleted mid-session must take
            # the "vanished" path, never the first-run empty reset.
            self._seen_file = True
            # utf-8-sig: a BOM from a hand edit (Windows Notepad) is not corruption.
            loaded = json.loads(content.decode("utf-8-sig"))
            if _nests_deeper_than(loaded, MAX_NESTING_DEPTH):
                raise ValueError("memory file nests deeper than the store schema")
            json.dumps(loaded, allow_nan=False)
        except FileNotFoundError:
            if self._seen_file:
                if self.available:
                    bootstrap.warn(
                        bootstrap.MEMORY_FILE_VANISHED_MESSAGE.format(path=self.path)
                    )
                self.available = False
                return
            self.data = _empty_store()
            self.available = True
            if not self.read_only:
                try:
                    self._write()
                except MemoryUnavailableError:
                    pass
            return
        except (ValueError, UnicodeDecodeError, RecursionError):
            # RecursionError is not a ValueError: deep nesting is corruption too.
            self._backup_corrupt_file(content)
            self.available = False
            return
        except OSError:
            if self.available and os.path.islink(self.path):
                bootstrap.warn(bootstrap.MEMORY_SYMLINK_MESSAGE.format(path=self.path))
            self.available = False
            return

        if (
            isinstance(loaded, dict)
            and type(loaded.get("version")) is int
            and loaded["version"] > SCHEMA_VERSION
        ):
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
            self._backup_corrupt_file(content)
            self.available = False
            return
        self.data = loaded
        self.available = True

    def _backup_corrupt_file(self, content: bytes | None) -> None:
        """Back up the bytes already read, never re-opening the path."""
        if self.read_only or content is None:
            return
        digest = hashlib.sha256(content).hexdigest()[:8]
        if glob.glob(f"{glob.escape(self.path)}.broken-*-{digest}"):
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = f"{self.path}.broken-{stamp}-{digest}"
        try:
            fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as dst:
                dst.write(content)
        except OSError:
            pass

    @staticmethod
    def _replace_with_retry(source: str, destination: str) -> None:
        for delay in REPLACE_RETRY_DELAYS:
            try:
                os.replace(source, destination)
                return
            except PermissionError:
                time.sleep(delay)
        os.replace(source, destination)

    def _write(self) -> None:
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
                f.flush()
                os.fsync(f.fileno())  # durable before the rename (power loss)
            self._replace_with_retry(tmp_path, self.path)
            self._seen_file = True
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

    def _append_changelog(
        self, op: str, collection: str, entry_id: int | None, before, after
    ) -> None:
        log_path = f"{self.path}.log"
        record = {
            "ts": self.now_iso(),
            "pid": os.getpid(),
            "op": op,
            "collection": collection,
            "id": entry_id,
            "before": before,
            "after": after,
        }
        try:
            line = json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | NO_FOLLOW
            fd = os.open(log_path, flags, 0o600)
            try:
                f = os.fdopen(fd, "a", encoding="utf-8", newline="\n")
            except BaseException:
                os.close(fd)
                raise
            with f:
                self._tighten(log_path, f.fileno())
                f.write(line)
        except (OSError, ValueError) as exc:
            bootstrap.warn(
                bootstrap.CHANGELOG_FAILED_MESSAGE.format(path=log_path, cause=exc)
            )

    def save(self) -> None:
        """Persist `self.data` atomically using a private temporary file.

        Only call it inside `_locked()` after mutating freshly reloaded data:
        on its own it does not reload, so a bare call writes whatever is in
        memory (read-modify-write is the caller's job).
        """
        self._require_available()
        self._require_writable()
        with self._locked(reload=False):
            self._write()

    @staticmethod
    def now_iso() -> str:
        """Current local time as an ISO-8601 string with timezone offset."""
        return datetime.datetime.now().astimezone().isoformat()

    def _require_available(self) -> None:
        if not self.available:
            raise MemoryUnavailableError(
                f"Memory store is unavailable (missing, inaccessible or invalid file at {self.path}). "
                "The original file was not overwritten. Tell the user memory is unavailable "
                "and keep operating without it."
            )

    def _require_writable(self) -> None:
        if self.read_only:
            raise MemoryReadOnlyError(
                f"Investor memory at {self.path} is read-only: the filesystem does not "
                "support file locking, so writes are refused to avoid losing data. "
                "Reads still work; tell the user the operator must point "
                "WALLET_MEMORY_PATH to a local disk."
            )

    def _collection(self, collection: str) -> list:
        if collection not in COLLECTIONS:
            raise ValueError(f"Unknown collection: {collection}")
        self._require_available()
        return self.data.setdefault(collection, [])

    def next_id(self, collection: str) -> int:
        with self._locked():
            entries = self._collection(collection)
            return max((entry.get("id", 0) for entry in entries), default=0) + 1

    def add(self, collection: str, entry: dict) -> dict:
        with self._locked():
            self._require_available()
            self._require_writable()
            entry["id"] = self.next_id(collection)
            entry.setdefault("created_at", self.now_iso())
            self._collection(collection).append(entry)
            self._append_changelog(
                "create", collection, entry["id"], None, copy.deepcopy(entry)
            )
            self.save()
            return entry

    def get_all(self, collection: str) -> list:
        with self._locked():
            return list(self._collection(collection))

    def find(self, collection: str, entry_id: int) -> dict | None:
        with self._locked():
            for entry in self._collection(collection):
                if entry.get("id") == entry_id:
                    return entry
            return None

    def update(self, collection: str, entry_id: int, changes: dict) -> dict | None:
        with self._locked():
            entry = self.find(collection, entry_id)
            if entry is None:
                return None
            self._require_writable()
            before = copy.deepcopy(entry)
            entry.update(changes)
            self._append_changelog(
                "update", collection, entry_id, before, copy.deepcopy(entry)
            )
            self.save()
            return entry

    @staticmethod
    def _clean_text(value: str, field: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field} must be text")
        text = value.strip()
        if not text:
            raise ValueError(f"{field} must not be empty")
        return text

    def get_wallet_goal(self) -> dict | None:
        with self._locked():
            self._require_available()
            return self.data.get("wallet_goal")

    def set_wallet_goal(self, text: str) -> dict:
        with self._locked():
            self._require_available()
            self._require_writable()
            goal = {
                "text": self._clean_text(text, "text"),
                "updated_at": self.now_iso(),
            }
            before = copy.deepcopy(self.data.get("wallet_goal"))
            self.data["wallet_goal"] = goal
            self._append_changelog(
                "set", "wallet_goal", None, before, copy.deepcopy(goal)
            )
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
        with self._locked():
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
        with self._locked():
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
        with self._locked():
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

    def create_price_alert(self, ticker: str, direction: str, limit_price) -> dict:
        """Create an alert with state='active'."""
        with self._locked():
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
                raise ValueError(
                    "limit_price must be a finite number greater than zero"
                )
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
        with self._locked():
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
        with self._locked():
            self._require_available()
            alert = self.find("alerts", alert_id)
            if alert is None:
                return None
            if alert.get("state") != "active":
                raise StateConflictError(
                    f"Price alert {alert_id} is already {alert.get('state')}: only active "
                    "alerts can be cancelled. Use list_price_alerts to check alert states; "
                    "create a new alert with create_price_alert if one is still needed."
                )
            return self.update("alerts", alert_id, {"state": "cancelled"})

    def evaluate_alerts(self, quotes: dict) -> list:
        """Evaluate all active alerts against current quotes (session open only).

        quotes maps ticker -> current price. Tickers absent from `quotes`
        (check failed) are skipped and stay active. Triggers are terminal:
        a triggered alert is persisted as 'triggered' and never fires again.
        The alerts are re-read under the lock, so one already triggered by
        another process is not fired twice. All satisfied alerts are
        persisted in ONE atomic save, so a save failure leaves the file
        untouched and every alert still active for the next session.
        """
        with self._locked():
            self._require_available()
            self._require_writable()
            triggered = []
            for alert in self.get_all("alerts"):
                if alert.get("state") != "active" or not alert_is_valid(alert):
                    continue
                price = quotes.get(alert["ticker"].strip().upper())
                if price is None:
                    continue
                limit = float(alert["limit_price"])
                hit = (
                    price <= limit if alert["direction"] == "below" else price >= limit
                )
                if hit:
                    before = copy.deepcopy(alert)
                    alert.update(
                        {
                            "state": "triggered",
                            "triggered_at": self.now_iso(),
                            "triggered_price": price,
                        }
                    )
                    self._append_changelog(
                        "trigger", "alerts", alert["id"], before, copy.deepcopy(alert)
                    )
                    triggered.append(alert)
            if triggered:
                self.save()
            return triggered

    def session_digest(self, recent_insights_limit: int = 10) -> dict:
        """Digest of the investor memory for the session bootstrap."""
        with self._locked():
            self._require_available()
            theses_by_ticker: dict = {}
            for thesis in self.get_all("theses"):
                theses_by_ticker.setdefault(thesis.get("ticker"), []).append(thesis)
            return {
                "wallet_goal": self.data.get("wallet_goal"),
                "theses": theses_by_ticker,
                "rules": self.get_rules(),
                "pending_decisions": [
                    d
                    for d in self.get_all("decisions")
                    if d.get("outcome") == "pending"
                ],
                "recent_insights": self.get_all("insights_log")[-recent_insights_limit:]
                if recent_insights_limit
                else [],
            }
