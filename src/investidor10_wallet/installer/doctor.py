import argparse
import asyncio
import errno
import json
import os
import platform
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import filelock

from .. import __version__, local_files, wallet_client, wallet_config
from .clients import ADAPTERS, ClaudeAdapter

LABELS = {"ok": "[ok]", "warn": "[aviso]", "fail": "[falha]"}
DESKTOP_CONFIG_MAX_BYTES = 1048576
PRODUCT_MARKER = "mcp-investidor10-wallet"
UNSUPPORTED_LOCK_ERRNOS = {errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}
INSTALL_ACTION = "Rode 'uvx mcp-investidor10-wallet install' num terminal."
CONFIGURE_ACTION = (
    "Peça ao assistente 'configure minha carteira' ou rode "
    "'mcp-investidor10-wallet configure' num terminal."
)


@dataclass(frozen=True)
class Check:
    id: str
    status: str
    cause: str
    action: str = ""


def _tilde(path, home: Path) -> str:
    text = str(path)
    base = str(home)
    if text == base:
        return "~"
    if text.startswith((base + os.sep, base + "/")):
        text = "~" + text[len(base) :]
    return text.replace("\\", "/")


def sanitize(text: str, home: Path, secrets=()) -> str:
    result = text
    for variant in {str(home), Path(home).as_posix()}:
        if variant:
            result = result.replace(variant, "~")
    for secret in secrets:
        if secret:
            result = result.replace(secret, "<oculto>")
    name = Path(home).name
    if len(name) >= 3:
        result = re.sub(re.escape(name), "<usuario>", result, flags=re.IGNORECASE)
    return result


def _runner() -> Check:
    if shutil.which("uvx") or shutil.which("uv"):
        return Check("runner", "ok", "O 'uv' foi encontrado.")
    return Check(
        "runner",
        "fail",
        "O 'uv' não foi encontrado: o plugin do Claude Desktop roda o servidor com ele.",
        "Instale o 'uv' seguindo docs/INSTALACAO-DESKTOP.md e abra um terminal novo.",
    )


def _configuration(state: wallet_config.WalletState) -> Check:
    if state.status == "configured":
        kind = "restrita" if state.mode == "restricted" else "pública"
        mask = "ligado" if state.mask_values else "desligado"
        credential = "presente" if state.share_hash else "ausente"
        origin = (
            "arquivo de configuração local"
            if state.origin == "file"
            else "variável de ambiente WALLET_ID"
        )
        return Check(
            "config",
            "ok",
            f"Carteira {kind}, mascaramento {mask}, credencial {credential}, "
            f"origem: {origin}.",
        )
    reasons = {
        "missing": "Nenhuma carteira está configurada.",
        "unreadable": (
            "O arquivo de configuração está ilegível ou com o link inválido."
        ),
        "future_version": (
            "A configuração foi criada por uma versão mais nova do produto."
        ),
    }
    action = (
        "Atualize o mcp-investidor10-wallet; a configuração não será alterada."
        if state.reason == "future_version"
        else CONFIGURE_ACTION
    )
    return Check(
        "config",
        "fail",
        reasons.get(state.reason or "", reasons["unreadable"]),
        action,
    )


def _permissions(home: Path) -> Check | None:
    if sys.platform == "win32":
        return None
    path = wallet_config.config_path(home)
    try:
        mode = os.lstat(path).st_mode & 0o777
    except OSError:
        return None
    if mode & 0o077:
        return Check(
            "config_permissions",
            "warn",
            "O arquivo de configuração pode ser lido por outros usuários da máquina.",
            "Rode 'chmod 600 ~/.investidor10/config.json'.",
        )
    return Check("config_permissions", "ok", "O arquivo de configuração é privado.")


def _wallet(state: wallet_config.WalletState) -> tuple[list[Check], str]:
    result = asyncio.run(wallet_client.check_wallet(state.wallet_id, state.share_hash))
    restricted = state.mode == "restricted"
    if result == "valid":
        checks = [Check("wallet", "ok", "A fonte reconhece a carteira configurada.")]
        if restricted:
            checks.append(_exposure(state))
        return checks, result
    if result == "access_denied":
        if restricted:
            check = Check(
                "wallet",
                "fail",
                "O Investidor10 recusou o acesso: o link restrito pode ter sido "
                "renovado ou a carteira pode ter virado privada.",
                "Gere o link de compartilhamento atual no site e rode "
                "'mcp-investidor10-wallet configure'.",
            )
        else:
            check = Check(
                "wallet",
                "fail",
                "O Investidor10 recusou o acesso: a carteira pode ser privada ou "
                "restrita.",
                "Torne a carteira pública ou restrita no site; se for restrita, "
                "configure com o link completo (com o trecho ?h=...).",
            )
        return [check], result
    if result == "not_found":
        return [
            Check(
                "wallet",
                "fail",
                "A carteira configurada não existe no Investidor10.",
                CONFIGURE_ACTION,
            )
        ], result
    return [
        Check(
            "wallet",
            "warn",
            "O Investidor10 não respondeu agora, então a carteira não foi validada.",
            "Tente de novo em alguns minutos.",
        )
    ], result


def _exposure(state: wallet_config.WalletState) -> Check:
    result = asyncio.run(wallet_client.check_wallet(state.wallet_id, None))
    if result == "valid":
        return Check(
            "restricted_exposure",
            "warn",
            "A carteira restrita responde sem a credencial: na prática ela está "
            "pública e indexável por buscadores.",
            "Ative o compartilhamento restrito no site do Investidor10 e gere um "
            "novo link.",
        )
    return Check(
        "restricted_exposure",
        "ok",
        "Sem a credencial a fonte recusa o acesso: a carteira é restrita de fato.",
    )


def _memory(home: Path, environ, lock_timeout: float) -> list[Check]:
    override = environ.get("WALLET_MEMORY_PATH")
    path = Path(override) if override else home / ".investidor10" / "memory.json"
    shown = _tilde(path, home)
    directory = path.parent
    if directory.is_dir():
        writable = os.access(directory, os.W_OK | os.X_OK)
    else:
        writable = os.access(home, os.W_OK | os.X_OK)
    if writable and path.exists():
        writable = os.access(path, os.R_OK | os.W_OK)
    if not writable:
        return [
            Check(
                "memory",
                "fail",
                f"Sem permissão de escrita na memória ({shown}).",
                f"Ajuste as permissões da pasta e do arquivo ({shown}) para o seu "
                "usuário, ou aponte WALLET_MEMORY_PATH para outro lugar.",
            )
        ]
    checks = [
        Check(
            "memory", "ok", f"A memória é acessível para leitura e escrita ({shown})."
        )
    ]
    if directory.is_dir():
        checks.append(_lock(path, lock_timeout))
    return checks


def _lock(path: Path, timeout: float) -> Check:
    lock = filelock.FileLock(
        f"{path}.lock", timeout=timeout, mode=0o600, fallback_to_soft=False
    )
    try:
        lock.acquire()
    except filelock.Timeout:
        return Check(
            "memory_lock",
            "warn",
            "Outro processo está segurando a trava da memória.",
            "Feche os clientes que estejam gravando e rode o diagnóstico de novo.",
        )
    except OSError as exc:
        if exc.errno in UNSUPPORTED_LOCK_ERRNOS:
            return Check(
                "memory_lock",
                "warn",
                "Este disco não suporta a trava da memória: o servidor ficaria "
                "em modo somente leitura.",
                "Aponte WALLET_MEMORY_PATH para um disco local.",
            )
        return Check(
            "memory_lock",
            "fail",
            "Não foi possível usar o arquivo de trava da memória.",
            "Confira as permissões da pasta da memória.",
        )
    lock.release()
    return Check("memory_lock", "ok", "A trava da memória está disponível.")


def _desktop_config_path(home: Path, environ, platform_name: str) -> Path | None:
    if platform_name == "darwin":
        return (
            home
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if platform_name == "win32":
        base = environ.get("APPDATA")
        root = Path(base) if base else home / "AppData" / "Roaming"
        return root / "Claude" / "claude_desktop_config.json"
    return None


def _desktop_manual_entry(home: Path, environ, platform_name: str) -> Check | None:
    path = _desktop_config_path(home, environ, platform_name)
    if path is None:
        return None
    try:
        data = json.loads(
            local_files.read_bytes_no_follow(path, DESKTOP_CONFIG_MAX_BYTES).decode(
                "utf-8-sig"
            )
        )
    except (OSError, ValueError, RecursionError):
        return Check(
            "desktop_manual_entry",
            "ok",
            "Nenhuma entrada manual do produto no Claude Desktop.",
        )
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    found = False
    if isinstance(servers, dict):
        for name, entry in servers.items():
            blob = json.dumps(entry, ensure_ascii=False) if entry else ""
            if name == "carteira" or PRODUCT_MARKER in blob:
                found = True
    if not found:
        return Check(
            "desktop_manual_entry",
            "ok",
            "Nenhuma entrada manual do produto no Claude Desktop.",
        )
    return Check(
        "desktop_manual_entry",
        "warn",
        f"O arquivo {_tilde(path, home)} tem uma entrada manual do produto: ela "
        "duplica o plugin e pode gerar duas conexões.",
        "Remova a entrada do servidor da carteira em 'mcpServers' e reinicie o "
        "Claude Desktop.",
    )


def _clients() -> list[Check]:
    detected = [adapter for adapter in ADAPTERS if adapter.detect()]
    if not detected:
        return [
            Check(
                "clients",
                "warn",
                "Nenhum CLI de agente foi encontrado, então não consigo ver se o "
                "plugin está no Claude Desktop.",
                "Confira em Customize > Plugins do Claude Desktop se o plugin está "
                "instalado, ou instale um CLI e rode 'mcp-investidor10-wallet "
                "install'.",
            )
        ]
    present = []
    checks = []
    claude_state = None
    for adapter in detected:
        if isinstance(adapter, ClaudeAdapter):
            claude_state = adapter.inspect()
            if claude_state.synced:
                present.append(
                    f"{adapter.label} (plugin sincronizado pelo Claude Desktop)"
                )
            elif claude_state.plugin_server or claude_state.local:
                present.append(f"{adapter.label} (plugin)")
            elif claude_state.old_registration:
                present.append(f"{adapter.label} (servidor registrado)")
        elif adapter.list_existing():
            present.append(f"{adapter.label} (servidor registrado)")
    if present:
        checks.append(
            Check("clients", "ok", "Produto presente em: " + ", ".join(present) + ".")
        )
    else:
        checks.append(
            Check(
                "clients",
                "fail",
                "O produto não está registrado em nenhum cliente detectado ("
                + ", ".join(adapter.label for adapter in detected)
                + ").",
                INSTALL_ACTION,
            )
        )
    if claude_state is not None:
        plugin = claude_state.plugin_server or claude_state.synced or claude_state.local
        if claude_state.old_registration and plugin:
            checks.append(
                Check(
                    "duplicate",
                    "warn",
                    "O servidor da carteira aparece duas vezes no Claude Code (registro "
                    "antigo mais plugin): são 40 tools em vez de 20.",
                    "Rode 'claude mcp remove carteira -s user'.",
                )
            )
        else:
            checks.append(
                Check("duplicate", "ok", "Um só servidor da carteira no Claude Code.")
            )
        checks.append(_versions(claude_state.plugin_version))
    else:
        checks.append(_versions(None))
    return checks


def _versions(plugin_version: str | None) -> Check:
    if plugin_version is None:
        return Check("versions", "ok", f"Pacote na versão {__version__}.")
    if plugin_version != __version__:
        return Check(
            "versions",
            "warn",
            f"O plugin está na versão {plugin_version} e o pacote na {__version__}.",
            "Atualize o plugin ou rode 'mcp-investidor10-wallet install'.",
        )
    return Check("versions", "ok", f"Pacote e plugin na mesma versão ({__version__}).")


def collect(
    home: Path | None = None,
    environ=None,
    platform_name: str | None = None,
    lock_timeout: float = 1.0,
) -> list[Check]:
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    platform_name = platform_name or sys.platform
    checks = [_runner()]
    state = wallet_config.resolve_state(environ, home)
    checks.append(_configuration(state))
    permissions = _permissions(home)
    if permissions is not None and state.origin == "file":
        checks.append(permissions)
    if state.status == "configured":
        wallet_checks, _ = _wallet(state)
        checks.extend(wallet_checks)
    checks.extend(_memory(home, environ, lock_timeout))
    checks.extend(_clients())
    desktop = _desktop_manual_entry(home, environ, platform_name)
    if desktop is not None:
        checks.append(desktop)
    return checks


def render(checks: list[Check]) -> str:
    lines = [f"Diagnóstico do mcp-investidor10-wallet {__version__}", ""]
    for check in checks:
        if check.status == "ok":
            lines.append(f"{LABELS['ok']} {check.id}: {check.cause}")
            continue
        lines.append(f"{LABELS[check.status]} {check.id}")
        lines.append(f"    causa: {check.cause}")
        lines.append(f"    ação: {check.action}")
    failures = sum(1 for c in checks if c.status == "fail")
    warnings = sum(1 for c in checks if c.status == "warn")
    lines += [
        "",
        f"Resultado: {failures} falha(s), {warnings} aviso(s).",
        "",
        "--- cole abaixo numa issue ---",
        (
            f"mcp-investidor10-wallet {__version__} | sistema: {platform.system()} | "
            f"python: {platform.python_version()}"
        ),
        f"resultado: {failures} falha(s), {warnings} aviso(s)",
        "checagens: " + ", ".join(f"{c.id}={c.status}" for c in checks),
        "--- fim ---",
    ]
    return "\n".join(lines)


def _secrets(home: Path, environ) -> list[str]:
    state = wallet_config.resolve_state(environ, home)
    values = [state.wallet_id, state.share_hash]
    values += [environ.get("WALLET_ID"), environ.get("WALLET_HASH")]
    return [str(value) for value in values if value]


def run(argv: list[str]) -> int:
    """Entry point of the doctor subcommand."""
    argparse.ArgumentParser(
        prog="mcp-investidor10-wallet doctor",
        description="Confere a instalação e imprime um resumo sem dados sensíveis, pronto para colar numa issue.",
    ).parse_args(argv)
    home = Path.home()
    environ = os.environ
    checks = collect(home=home, environ=environ)
    print(sanitize(render(checks), home, _secrets(home, environ)))
    return 1 if any(c.status == "fail" for c in checks) else 0
