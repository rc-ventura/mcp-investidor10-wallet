"""Long-term memory store for the investor agent.

Persists the investor's knowledge base (goal, theses, rules, decisions,
insight log, price alerts) to a single local JSON file with a versioned
schema. Writes are atomic (tmp + rename) and a corrupted or future-versioned
file degrades the store into an explicitly unavailable mode instead of
crashing the MCP server or losing data.

Schema v1 (see specs/001-mcp-investidor10-wallet/data-model.md):
    version, wallet_goal, theses, rules, decisions, insights_log, alerts
"""

import datetime
import glob
import json
import os
import re

SCHEMA_VERSION = 1
COLLECTIONS = ("theses", "rules", "decisions", "insights_log", "alerts")


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


class MemoryStore:
    """JSON-file backed memory store with atomic persistence and degraded mode."""

    def __init__(self, path: str):
        self.path = path
        self.available = True
        self.data: dict = _empty_store()
        self._load()

    # ------------------------------------------------------------------ load/save

    def _load(self) -> None:
        if not os.path.exists(self.path):
            # First run: create an empty v1 store on disk.
            self.data = _empty_store()
            self.save()
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict) or loaded.get("version", 0) > SCHEMA_VERSION:
                # Valid JSON, unknown schema version: refuse to interpret or
                # rewrite it. Keep the file untouched and degrade.
                self.available = False
                return
            self.data = loaded
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Corrupted file: preserve the original as a .broken-<timestamp>
            # backup before anything else could overwrite it, then degrade.
            self._backup_corrupt_file()
            self.available = False

    def _backup_corrupt_file(self) -> None:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{self.path}.broken-{stamp}"
        try:
            if not glob.glob(backup_path):
                with open(self.path, encoding="utf-8", errors="replace") as src:
                    content = src.read()
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(content)
        except OSError:
            # Backup is best-effort; degraded mode is still the safe outcome.
            pass

    def save(self) -> None:
        """Persist the store atomically: write to a tmp file, then rename."""
        self._require_available()
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def now_iso() -> str:
        """Current local time as an ISO-8601 string with timezone offset."""
        return datetime.datetime.now().astimezone().isoformat()

    def _require_available(self) -> None:
        if not self.available:
            raise MemoryUnavailableError(
                "Memory store is unavailable (corrupted file or unsupported schema "
                f"version at {self.path}). The original file was preserved."
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
