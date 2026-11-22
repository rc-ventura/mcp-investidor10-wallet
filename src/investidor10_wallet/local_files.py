import os
import stat
import tempfile
import time
from pathlib import Path

NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
BINARY = getattr(os, "O_BINARY", 0)
REPLACE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8)


def ensure_private_dir(directory: Path) -> None:
    if os.path.lexists(directory):
        st = os.lstat(directory)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
            raise OSError(f"{directory} não é um diretório regular")
    else:
        Path(directory).mkdir(mode=0o700, parents=True, exist_ok=True)
        st = os.lstat(directory)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
            raise OSError(f"{directory} não é um diretório regular")
    os.chmod(directory, 0o700)


def ensure_not_symlink(path: Path) -> None:
    if os.path.lexists(path) and stat.S_ISLNK(os.lstat(path).st_mode):
        raise OSError(f"{path} não pode ser um link simbólico")


def read_bytes_no_follow(path, limit: int | None = None) -> bytes:
    fd = os.open(path, os.O_RDONLY | NO_FOLLOW | BINARY)
    with os.fdopen(fd, "rb") as f:
        if limit is None:
            return f.read()
        content = f.read(limit + 1)
    if len(content) > limit:
        raise OSError(f"{path} excede o tamanho máximo de {limit} bytes")
    return content


def replace_with_retry(source, destination) -> None:
    for delay in REPLACE_RETRY_DELAYS:
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            time.sleep(delay)
    os.replace(source, destination)


def write_private_atomic(path, data: bytes, prefix: str) -> None:
    ensure_not_symlink(Path(path))
    tmp_path = None
    try:
        # mkstemp-backed files are created 0600, so the data is never world-readable
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=os.path.dirname(os.path.abspath(path)),
            prefix=prefix,
            delete=False,
        ) as f:
            tmp_path = f.name
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        replace_with_retry(tmp_path, path)
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
