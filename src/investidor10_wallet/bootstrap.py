import math
import os
import re
import stat
import sys
import tempfile
from datetime import datetime
from pathlib import Path

MISSING_WALLET_ID_MESSAGE = (
    "WALLET_ID não configurado. Defina a variável de ambiente WALLET_ID com o ID da sua "
    "carteira. O ID aparece na URL pública: investidor10.com.br/carteira/<ID>. "
    "Depois, reinicie o servidor."
)

INVALID_WALLET_ID_MESSAGE = (
    "WALLET_ID={value!r} inválido: use apenas dígitos. O ID aparece na URL pública: "
    "investidor10.com.br/carteira/<ID>. Depois, reinicie o servidor."
)

INVALID_NUMBER_MESSAGE = (
    "{name}={value!r} inválido: deve ser um número finito >= 0 (default {default}). "
    "Corrija o ambiente e reinicie o servidor."
)

WALLET_NOT_FOUND_MESSAGE = (
    "Carteira {wallet_id} não encontrada ou não é pública. Confira o ID na URL da carteira e, "
    "nas configurações do Investidor10, deixe a carteira pública. Depois, reinicie o servidor."
)

WALLET_PRIVATE_MESSAGE = (
    "Carteira {wallet_id} é privada. Nas configurações do Investidor10, deixe a carteira "
    "pública e reinicie o servidor."
)

PROBE_UNAVAILABLE_MESSAGE = (
    "Não foi possível validar a carteira {wallet_id} agora (fonte indisponível). O servidor "
    "iniciará mesmo assim; as ferramentas de dados informarão o erro quando falhar."
)

MIGRATION_FAILED_MESSAGE = (
    "Não foi possível migrar a memória de {legacy} para {canonical} ({cause}). "
    "Corrija as permissões do diretório {directory} e reinicie — seus dados em {legacy} "
    "não foram alterados."
)

CANONICAL_DIR_FAILED_MESSAGE = (
    "Não foi possível preparar o diretório de memória {directory} ({cause}). "
    "Verifique as permissões de escrita (0700) e reinicie o servidor."
)

MIGRATED_MESSAGE = "Memória migrada de {legacy} para {canonical}."

CONFLICT_RESOLVED_MESSAGE = (
    "Memória: {canonical} em uso. O arquivo antigo {legacy} foi preservado como {backup} "
    "e não é mais utilizado."
)

CANONICAL_DIR = Path.home() / ".investidor10"


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def fail(message: str) -> None:
    raise SystemExit(message)


def _parse_float(name: str, raw: str, default: str, environ) -> float:
    value = environ.get(name, default)
    try:
        number = float(value)
    except (TypeError, ValueError):
        fail(INVALID_NUMBER_MESSAGE.format(name=name, value=value, default=default))
    if not math.isfinite(number) or number < 0:
        fail(INVALID_NUMBER_MESSAGE.format(name=name, value=value, default=default))
    return number


def load_config(environ=None) -> dict:
    """Parse the operator environment; abort with PT-BR guidance on bad config."""
    environ = os.environ if environ is None else environ
    wallet_id = str(environ.get("WALLET_ID", "")).strip()
    if not wallet_id:
        fail(MISSING_WALLET_ID_MESSAGE)
    if not re.fullmatch(r"[0-9]+", wallet_id):
        fail(INVALID_WALLET_ID_MESSAGE.format(value=wallet_id))
    return {
        "wallet_id": wallet_id,
        "ttl_seconds": _parse_float("WALLET_CACHE_TTL_SECONDS", "", "600", environ),
        "max_stale_seconds": _parse_float(
            "WALLET_CACHE_MAX_STALE_SECONDS", "", "86400", environ
        ),
    }


def _ensure_canonical_dir(directory: Path) -> None:
    if os.path.lexists(directory):
        st = os.lstat(directory)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
            raise OSError(f"{directory} não é um diretório regular")
    else:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = os.lstat(directory)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
            raise OSError(f"{directory} não é um diretório regular")
    os.chmod(directory, 0o700)


def _ensure_not_symlink(path: Path) -> None:
    if os.path.lexists(path) and stat.S_ISLNK(os.lstat(path).st_mode):
        raise OSError(f"{path} não pode ser um link simbólico")


def _atomic_copy(source: Path, destination: Path) -> os.stat_result:
    _ensure_canonical_dir(destination.parent)
    _ensure_not_symlink(destination)
    _ensure_not_symlink(source)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    src_fd = os.open(source, os.O_RDONLY | nofollow)
    with os.fdopen(src_fd, "rb") as src_file:
        src_stat = os.fstat(src_file.fileno())
        if not stat.S_ISREG(src_stat.st_mode):
            raise OSError(f"{source} não é um arquivo regular")
        content = src_file.read()
    fd, tmp_name = tempfile.mkstemp(dir=destination.parent, prefix=".memory-")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(content)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, destination)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    dst_fd = os.open(destination, os.O_RDONLY | nofollow)
    with os.fdopen(dst_fd, "rb") as dst_file:
        written = dst_file.read()
    if written != content:
        raise OSError("copied content does not match the source")
    return src_stat


def resolve_memory_path(
    cwd: Path | None = None,
    home: Path | None = None,
    environ=None,
    now: datetime | None = None,
) -> str:
    """Resolve the memory file location: override, then canonical, then legacy migration."""
    environ = os.environ if environ is None else environ
    override = environ.get("WALLET_MEMORY_PATH")
    if override:
        return override
    cwd = Path.cwd() if cwd is None else cwd
    home = Path.home() if home is None else home
    now = datetime.now() if now is None else now
    canonical = home / ".investidor10" / "memory.json"
    legacy = cwd / "memory.json"
    if os.path.abspath(legacy) == os.path.abspath(canonical):
        try:
            _ensure_canonical_dir(canonical.parent)
            _ensure_not_symlink(canonical)
        except OSError as exc:
            fail(
                CANONICAL_DIR_FAILED_MESSAGE.format(
                    directory=canonical.parent, cause=exc
                )
            )
        return str(canonical)
    canonical_exists = os.path.lexists(canonical)
    legacy_exists = os.path.lexists(legacy)
    if canonical_exists and legacy_exists:
        try:
            _ensure_canonical_dir(canonical.parent)
            _ensure_not_symlink(canonical)
        except OSError as exc:
            fail(
                CANONICAL_DIR_FAILED_MESSAGE.format(
                    directory=canonical.parent, cause=exc
                )
            )
        stamp = now.strftime("%Y%m%d-%H%M%S-%f")
        backup = legacy.with_name(f"memory.json.legacy-{stamp}")
        try:
            if os.path.lexists(backup):
                raise FileExistsError(str(backup))
            legacy.rename(backup)
        except OSError:
            backup = legacy
        warn(
            CONFLICT_RESOLVED_MESSAGE.format(
                canonical=canonical, legacy=legacy, backup=backup
            )
        )
        return str(canonical)
    if legacy_exists:
        try:
            src_stat = _atomic_copy(legacy, canonical)
            cur_stat = os.lstat(legacy)
            if cur_stat.st_ino != src_stat.st_ino or cur_stat.st_dev != src_stat.st_dev:
                raise OSError("arquivo legado alterado durante a migração")
            legacy.unlink()
        except OSError as exc:
            try:
                canonical.unlink()
            except OSError:
                pass
            fail(
                MIGRATION_FAILED_MESSAGE.format(
                    legacy=legacy,
                    canonical=canonical,
                    cause=exc,
                    directory=canonical.parent,
                )
            )
        warn(MIGRATED_MESSAGE.format(legacy=legacy, canonical=canonical))
        return str(canonical)
    try:
        _ensure_canonical_dir(canonical.parent)
        _ensure_not_symlink(canonical)
    except OSError as exc:
        fail(CANONICAL_DIR_FAILED_MESSAGE.format(directory=canonical.parent, cause=exc))
    return str(canonical)
