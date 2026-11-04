import datetime
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from . import bootstrap, local_files

CONFIG_VERSION = 1
CONFIG_DIR_NAME = ".investidor10"
CONFIG_FILE_NAME = "config.json"
MAX_CONFIG_BYTES = 65536
MAX_LINK_CHARS = 4096

WALLET_ID_PATTERN = re.compile(r"[0-9]+")
SHARE_HASH_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,256}")
URL_PATTERN = re.compile(r"https?://[^\s<>\"'`“”‘’]+", re.IGNORECASE)
URL_TRAILING_CHARS = ".,;:!?)]}>"
SURROUNDING_CHARS = " \t\r\n\"'`“”‘’<>()[]{}.,;:!?"
WALLET_HOSTS = frozenset({"investidor10.com.br", "www.investidor10.com.br"})
HTTPS_PORT = 443

SOURCES = ("setup_page", "installer", "configure")

LINK_MESSAGES = {
    "empty": (
        "Cole o link da sua carteira do Investidor10 (ou só o número dela). Link "
        "de carteira pública: investidor10.com.br/carteira/<ID>."
    ),
    "not_recognized": (
        "Não reconheci esse texto como link de carteira. Cole o link completo da "
        "carteira (começa com https://investidor10.com.br/) ou só o número dela."
    ),
    "wrong_host": (
        "O link não é do Investidor10. Cole um link que comece com "
        "https://investidor10.com.br/ ou https://www.investidor10.com.br/."
    ),
    "multiple_links": (
        "Encontrei mais de um link do Investidor10 no texto. Cole apenas o link "
        "de uma carteira."
    ),
    "invalid_id": (
        "O número da carteira no link não é válido: ele deve conter apenas dígitos."
    ),
    "missing_credential": (
        "O link da carteira restrita está sem a credencial (o trecho ?h=...). "
        "Copie o link completo, como o Investidor10 mostra ao compartilhar."
    ),
    "invalid_credential": (
        "A credencial do link (o trecho ?h=...) não tem o formato esperado. "
        "Copie o link completo, sem alterar nada."
    ),
}


class LinkError(ValueError):
    def __init__(self, reason: str):
        super().__init__(LINK_MESSAGES[reason])
        self.reason = reason


class ConfigProblem(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class FutureVersionError(ValueError):
    pass


@dataclass(frozen=True)
class WalletLink:
    wallet_id: str = field(repr=False)
    share_hash: str | None = field(repr=False)
    mode: str


def _strip_url_tail(url: str) -> str:
    return url.rstrip(URL_TRAILING_CHARS)


def _classify_url(url: str):
    try:
        parts = urlsplit(url)
        port = parts.port
        hostname = parts.hostname
        has_userinfo = parts.username is not None or parts.password is not None
    except ValueError:
        return "other_host", None
    if hostname not in WALLET_HOSTS or has_userinfo:
        return "other_host", None
    if port not in (None, HTTPS_PORT):
        return "other_host", None
    if parts.scheme.lower() != "https":
        return "insecure", None
    return "wallet", parts


def _digits_or_refuse(candidate: str) -> str:
    if not WALLET_ID_PATTERN.fullmatch(candidate):
        raise LinkError("invalid_id")
    return candidate


def _credential(query: str) -> str:
    values = [
        value for key, value in parse_qsl(query, keep_blank_values=True) if key == "h"
    ]
    if not values or values == [""]:
        raise LinkError("missing_credential")
    if len(values) > 1 or not SHARE_HASH_PATTERN.fullmatch(values[0]):
        raise LinkError("invalid_credential")
    return values[0]


def _link_from_path(parts) -> WalletLink:
    segments = [segment for segment in parts.path.split("/") if segment]
    head = [segment.lower() for segment in segments[:2]]
    if head == ["wallet", "public"]:
        if len(segments) != 3:
            raise LinkError("not_recognized")
        wallet_id = _digits_or_refuse(segments[2])
        return WalletLink(wallet_id, _credential(parts.query), "restricted")
    if head[:1] == ["carteira"] and len(segments) >= 2:
        return WalletLink(_digits_or_refuse(segments[1]), None, "public")
    raise LinkError("not_recognized")


def parse_link(text: str) -> WalletLink:
    if not isinstance(text, str) or not text.strip():
        raise LinkError("empty")
    if len(text) > MAX_LINK_CHARS:
        raise LinkError("not_recognized")
    found = [_classify_url(_strip_url_tail(url)) for url in URL_PATTERN.findall(text)]
    wallet_urls = [parts for kind, parts in found if kind == "wallet"]
    if len(wallet_urls) > 1:
        raise LinkError("multiple_links")
    if wallet_urls:
        return _link_from_path(wallet_urls[0])
    if found:
        kinds = {kind for kind, _ in found}
        raise LinkError("not_recognized" if "insecure" in kinds else "wrong_host")
    candidate = text.strip().strip(SURROUNDING_CHARS)
    if WALLET_ID_PATTERN.fullmatch(candidate):
        return WalletLink(candidate, None, "public")
    raise LinkError("not_recognized")


def masked_wallet(wallet_id: str) -> str:
    return "…" + wallet_id[-2:]


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class LocalConfig:
    wallet_id: str = field(repr=False)
    share_hash: str | None = field(repr=False)
    mode: str
    mask_values: bool
    validated_at: str
    source: str

    @classmethod
    def from_dict(cls, data) -> "LocalConfig":
        if not isinstance(data, dict):
            raise ValueError("config must be a JSON object")
        version = data.get("version")
        if not _is_int(version):
            raise ValueError("version must be an integer")
        if version > CONFIG_VERSION:
            raise FutureVersionError(version)
        if version != CONFIG_VERSION:
            raise ValueError("unsupported version")
        wallet_id = data.get("wallet_id")
        if not isinstance(wallet_id, str) or not WALLET_ID_PATTERN.fullmatch(wallet_id):
            raise ValueError("wallet_id must be digits")
        if "share_hash" not in data:
            raise ValueError("share_hash must be present, null in public mode")
        mode = data.get("mode")
        share_hash = data.get("share_hash")
        if mode == "public":
            if share_hash is not None:
                raise ValueError("public mode has no credential")
        elif mode == "restricted":
            if not isinstance(share_hash, str) or not SHARE_HASH_PATTERN.fullmatch(
                share_hash
            ):
                raise ValueError("restricted mode needs a valid credential")
        else:
            raise ValueError("mode must be public or restricted")
        mask_values = data.get("mask_values")
        if not isinstance(mask_values, bool):
            raise ValueError("mask_values must be a boolean")
        validated_at = data.get("validated_at")
        if not isinstance(validated_at, str):
            raise ValueError("validated_at must be a string")
        datetime.datetime.fromisoformat(validated_at)
        source = data.get("source")
        if source not in SOURCES:
            raise ValueError("source is not recognized")
        return cls(wallet_id, share_hash, mode, mask_values, validated_at, source)

    def to_dict(self) -> dict:
        return {
            "version": CONFIG_VERSION,
            "wallet_id": self.wallet_id,
            "share_hash": self.share_hash,
            "mode": self.mode,
            "mask_values": self.mask_values,
            "validated_at": self.validated_at,
            "source": self.source,
        }


def config_path(home: Path) -> Path:
    return Path(home) / CONFIG_DIR_NAME / CONFIG_FILE_NAME


def read_config(path) -> LocalConfig:
    try:
        raw = local_files.read_bytes_no_follow(path, MAX_CONFIG_BYTES)
    except FileNotFoundError as exc:
        raise ConfigProblem("missing") from exc
    except OSError as exc:
        raise ConfigProblem("unreadable") from exc
    try:
        # utf-8-sig: a BOM from a hand edit is not corruption
        return LocalConfig.from_dict(json.loads(raw.decode("utf-8-sig")))
    except FutureVersionError as exc:
        raise ConfigProblem("future_version") from exc
    except (ValueError, RecursionError) as exc:
        raise ConfigProblem("unreadable") from exc


def write_config(home: Path, config: LocalConfig) -> None:
    validated = LocalConfig.from_dict(config.to_dict())
    directory = Path(home) / CONFIG_DIR_NAME
    local_files.ensure_private_dir(directory)
    payload = json.dumps(validated.to_dict(), ensure_ascii=False, indent=2)
    local_files.write_private_atomic(
        directory / CONFIG_FILE_NAME, payload.encode("utf-8"), prefix=".config-"
    )


@dataclass(frozen=True)
class WalletState:
    status: str
    reason: str | None = None
    origin: str | None = None
    mode: str | None = None
    wallet_id: str | None = field(default=None, repr=False)
    share_hash: str | None = field(default=None, repr=False)
    mask_values: bool = False

    @property
    def wallet(self) -> str | None:
        return None if self.wallet_id is None else masked_wallet(self.wallet_id)


_CACHE: dict[str, tuple[tuple, "LocalConfig | str"]] = {}


def _environment_mask(environ) -> bool:
    try:
        return bootstrap.parse_mask(environ)
    except SystemExit:
        # an unreadable privacy flag fails closed, toward hiding amounts
        return True


def _pending(reason: str, mask_values: bool) -> WalletState:
    return WalletState(status="pending", reason=reason, mask_values=mask_values)


def _from_environment(environ, env_mask: bool) -> WalletState:
    wallet_id = str(environ.get("WALLET_ID", "")).strip()
    if not WALLET_ID_PATTERN.fullmatch(wallet_id):
        return _pending("missing", env_mask)
    return WalletState(
        status="configured",
        origin="environment",
        mode="public",
        wallet_id=wallet_id,
        mask_values=env_mask,
    )


def _identity(st: os.stat_result) -> tuple:
    return (st.st_ino, st.st_size, st.st_mtime_ns)


def resolve_state(environ=None, home: Path | None = None) -> WalletState:
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    path = config_path(home)
    key = str(path)
    env_mask = _environment_mask(environ)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        _CACHE.pop(key, None)
        return _from_environment(environ, env_mask)
    except OSError:
        _CACHE.pop(key, None)
        return _pending("unreadable", env_mask)
    identity = _identity(st)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] == identity:
        outcome = cached[1]
    else:
        try:
            outcome = read_config(path)
        except ConfigProblem as problem:
            outcome = problem.reason
        _CACHE[key] = (identity, outcome)
    if isinstance(outcome, str):
        if outcome == "missing":
            _CACHE.pop(key, None)
            return _from_environment(environ, env_mask)
        return _pending(outcome, env_mask)
    return WalletState(
        status="configured",
        origin="file",
        mode=outcome.mode,
        wallet_id=outcome.wallet_id,
        share_hash=outcome.share_hash,
        mask_values=outcome.mask_values or env_mask,
    )
