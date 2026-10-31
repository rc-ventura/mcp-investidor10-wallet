import math
import os
import re
import stat
import sys
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

CANONICAL_DIR_FAILED_MESSAGE = (
    "Não foi possível preparar o diretório de memória {directory} ({cause}). "
    "Verifique as permissões de escrita (0700) e reinicie o servidor."
)

LOCK_UNSUPPORTED_MESSAGE = (
    "A memória em {path} está em um sistema de arquivos sem suporte a trava (ex.: pasta de "
    "rede). Leituras seguem funcionando, mas gravações serão recusadas para não perder dados. "
    "Aponte WALLET_MEMORY_PATH para um disco local (ex.: ~/.investidor10/memory.json) e "
    "reinicie."
)

CHANGELOG_FAILED_MESSAGE = (
    "Aviso: não foi possível registrar a mudança em {path} ({cause}); a gravação na "
    "memória seguiu normalmente."
)

TIGHTEN_FAILED_MESSAGE = (
    "Aviso: não foi possível restringir {path} a 0600 ({cause}); confira as permissões "
    "do arquivo, que pode estar legível por outros usuários."
)

MEMORY_SYMLINK_MESSAGE = (
    "A memória em {path} é um link simbólico e não será lida nem gravada: um link "
    "pode apontar a leitura para qualquer arquivo. Aponte WALLET_MEMORY_PATH para o "
    "arquivo real (não para o link) e reinicie o servidor."
)

MEMORY_FILE_VANISHED_MESSAGE = (
    "A memória em {path} sumiu com o servidor rodando. Ela não será recriada vazia para "
    "não apagar teses e regras em silêncio. Restaure o arquivo (o histórico está em "
    "{path}.log) ou reinicie o servidor para começar uma memória vazia."
)

INVALID_MASK_MESSAGE = (
    "WALLET_MASK_VALUES={value!r} inválido: use 1/true/yes/on para ligar ou "
    "0/false/no/off para desligar. Corrija o ambiente e reinicie o servidor."
)

MASK_ACTIVE_MESSAGE = "Modo privacidade ativo: montantes em reais e quantidades não serão enviados ao modelo."

MASK_ON = frozenset({"1", "true", "yes", "on"})
MASK_OFF = frozenset({"0", "false", "no", "off"})


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


def _parse_mask(environ) -> bool:
    raw = environ.get("WALLET_MASK_VALUES")
    if raw is None:
        return False
    value = str(raw).strip().lower()
    if value in MASK_ON:
        return True
    if value in MASK_OFF:
        return False
    fail(INVALID_MASK_MESSAGE.format(value=raw))


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
        "mask_values": _parse_mask(environ),
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


def resolve_memory_path(home: Path | None = None, environ=None) -> str:
    """Resolve the memory file location: explicit override, else the per-user canonical path."""
    environ = os.environ if environ is None else environ
    override = environ.get("WALLET_MEMORY_PATH")
    if override:
        return override
    home = Path.home() if home is None else home
    canonical = home / ".investidor10" / "memory.json"
    try:
        _ensure_canonical_dir(canonical.parent)
        _ensure_not_symlink(canonical)
    except OSError as exc:
        fail(CANONICAL_DIR_FAILED_MESSAGE.format(directory=canonical.parent, cause=exc))
    return str(canonical)
