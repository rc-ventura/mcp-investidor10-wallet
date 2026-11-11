import re
import shutil
import subprocess
from dataclasses import dataclass

from .. import __version__
from . import SERVER_ALIAS, ClientRegistration, RegisterOutcome

RUNNER_COMMAND = "uvx"
RUNNER_ARGS = [f"mcp-investidor10-wallet@{__version__}"]

PLUGIN_NAME = "investidor10-carteira"
PLUGIN_ID = f"{PLUGIN_NAME}@investidor10"
SYNCED_ID = f"{PLUGIN_NAME}@synced"
MARKETPLACE_NAME = "investidor10"
MARKETPLACE_SOURCE = f"rc-ventura/mcp-investidor10-wallet#v{__version__}"
YES_ANSWERS = ("s", "sim", "y", "yes", "atualizar")
DUPLICATION_WARNING = (
    "Atenção: o servidor da carteira ficou duplicado (registro separado mais o "
    "plugin); remova um dos dois para não ter tools em dobro."
)
LEGACY_PROMPT = (
    "Claude Code: foi encontrada uma instalação anterior ({found}). O plugin já "
    "traz o servidor. Remover e instalar o plugin na versão certa [s/N]? "
)


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=120
    )


@dataclass(frozen=True)
class ClaudeInstall:
    old_registration: bool
    plugin_server: bool
    synced: bool
    local: bool
    plugin_version: str | None


def _plugin_version(listing: str) -> str | None:
    lines = listing.splitlines()
    for index, line in enumerate(lines):
        if f"{PLUGIN_NAME}@" in line:
            for follow in lines[index + 1 : index + 5]:
                found = re.search(r"Version:\s*(\S+)", follow)
                if found:
                    return found.group(1)
                if "@" in follow:
                    break
    return None


def _ask_yes(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in YES_ANSWERS
    except (EOFError, OSError):
        return False


class ClientAdapter:
    client_id = ""
    binary = ""
    label = ""

    def detect(self) -> bool:
        return shutil.which(self.binary) is not None

    def list_existing(self) -> bool:
        proc = _run([self.binary, "mcp", "list"])
        return any(SERVER_ALIAS in line for line in proc.stdout.splitlines())

    def add_command(self, reg: ClientRegistration) -> list[str]:
        raise NotImplementedError

    def plugin_install_commands(self) -> list[list[str]]:
        raise NotImplementedError

    def register(self, reg: ClientRegistration) -> RegisterOutcome:
        exists = self.list_existing()
        if exists:
            try:
                answer = input(
                    f"{self.label}: o servidor '{SERVER_ALIAS}' já está registrado. "
                    "Atualizar [s/N] (Enter = pular)?\n"
                )
            except EOFError:
                answer = ""
            if answer.strip().lower() not in ("s", "sim", "y", "yes", "atualizar"):
                return RegisterOutcome(
                    self.client_id,
                    "skipped_present",
                    f"{self.label}: servidor '{SERVER_ALIAS}' já registrado — mantido.",
                )
        proc = _run(self.add_command(reg))
        if proc.returncode != 0:
            detail = proc.stderr.strip() or f"código {proc.returncode}"
            return RegisterOutcome(
                self.client_id,
                "failed",
                f"{self.label}: falha ao registrar — {detail}",
            )
        status = "updated" if exists else "registered"
        return RegisterOutcome(
            self.client_id,
            status,
            f"{self.label}: servidor '{SERVER_ALIAS}' registrado (reinicie a sessão do cliente).",
        )


class ClaudeAdapter(ClientAdapter):
    client_id = "claude"
    binary = "claude"
    label = "Claude Code"

    def _capture(self, *args: str) -> str:
        return _run([self.binary, *args]).stdout

    def list_existing(self) -> bool:
        for line in self._capture("mcp", "list").splitlines():
            if line.split(":", 1)[0].strip() == SERVER_ALIAS:
                return True
        return False

    def inspect(self) -> ClaudeInstall:
        servers = self._capture("mcp", "list")
        plugins = self._capture("plugin", "list")
        return ClaudeInstall(
            old_registration=self.list_existing(),
            plugin_server=any(
                line.strip().startswith(f"plugin:{PLUGIN_NAME}:")
                for line in servers.splitlines()
            ),
            synced=SYNCED_ID in plugins,
            local=PLUGIN_ID in plugins,
            plugin_version=_plugin_version(plugins),
        )

    def _marketplace_present(self) -> bool:
        pattern = re.compile(rf"(?<![\w/-]){MARKETPLACE_NAME}(?![\w-])")
        return bool(pattern.search(self._capture("plugin", "marketplace", "list")))

    def plugin_install_commands(self) -> list[list[str]]:
        return [
            [
                self.binary,
                "plugin",
                "marketplace",
                "add",
                MARKETPLACE_SOURCE,
            ],
            [self.binary, "plugin", "install", PLUGIN_ID],
        ]

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            reg.name,
            "--scope",
            "user",
            "--",
            reg.command,
            *reg.args,
        ]

    def register(self, reg: ClientRegistration) -> RegisterOutcome:
        outcome = super().register(reg)
        if outcome.status in ("registered", "updated") and (
            f"{PLUGIN_NAME}@" in self._capture("plugin", "list")
        ):
            outcome.message += " " + DUPLICATION_WARNING
        return outcome

    def install_plugin(self) -> tuple[RegisterOutcome, list[RegisterOutcome]]:
        installed = self._capture("plugin", "list")
        synced = SYNCED_ID in installed
        local = PLUGIN_ID in installed
        old_registration = self.list_existing()
        marketplace = self._marketplace_present()
        found = []
        if old_registration:
            found.append(f"registro '{SERVER_ALIAS}' em escopo de usuário")
        if local:
            found.append("cópia local do plugin")
        if marketplace and not synced:
            found.append(f"marketplace '{MARKETPLACE_NAME}'")
        remove = bool(found) and _ask_yes(LEGACY_PROMPT.format(found=", ".join(found)))
        warnings = []
        if remove:
            if old_registration:
                proc = _run([self.binary, "mcp", "remove", SERVER_ALIAS, "-s", "user"])
                if proc.returncode != 0:
                    warnings.append(DUPLICATION_WARNING)
            if local:
                _run([self.binary, "plugin", "uninstall", PLUGIN_ID])
            if marketplace and not synced:
                _run([self.binary, "plugin", "marketplace", "remove", MARKETPLACE_NAME])
        elif old_registration or (synced and local):
            warnings.append(DUPLICATION_WARNING)
        suffix = "".join(f" {w}" for w in warnings)
        if synced:
            return (
                RegisterOutcome(
                    self.client_id,
                    "skipped_present",
                    f"{self.label}: o plugin já chega pela sincronização do Claude "
                    f"Desktop ({SYNCED_ID}); não instalo uma cópia local.{suffix}",
                ),
                [],
            )
        if local and not remove:
            return (
                RegisterOutcome(
                    self.client_id,
                    "skipped_present",
                    f"{self.label}: o plugin já está instalado — mantido.{suffix}",
                ),
                [],
            )
        commands = self.plugin_install_commands()
        if marketplace and not remove:
            commands = commands[1:]
        for command in commands:
            proc = _run(command)
            if proc.returncode != 0:
                detail = proc.stderr.strip() or f"código {proc.returncode}"
                return (
                    RegisterOutcome(
                        self.client_id,
                        "failed",
                        f"{self.label}: falha ao instalar o plugin — {detail}",
                    ),
                    [],
                )
        return (
            RegisterOutcome(
                self.client_id,
                "registered",
                f"{self.label}: o servidor '{SERVER_ALIAS}' vem com o plugin, sem "
                f"registro separado.{suffix}",
            ),
            [
                RegisterOutcome(
                    self.client_id,
                    "registered",
                    f"{self.label}: plugin instalado (reinicie a sessão do cliente).",
                )
            ],
        )


class DevinAdapter(ClientAdapter):
    client_id = "devin"
    binary = "devin"
    label = "Devin CLI"

    def plugin_install_commands(self) -> list[list[str]]:
        return [
            [
                self.binary,
                "plugins",
                "install",
                "rc-ventura/mcp-investidor10-wallet#plugin",
                "-y",
            ]
        ]

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            "-s",
            "user",
            reg.name,
            "--",
            reg.command,
            *reg.args,
        ]


class CodexAdapter(ClientAdapter):
    client_id = "codex"
    binary = "codex"
    label = "Codex"

    def plugin_install_commands(self) -> list[list[str]]:
        if shutil.which(self.binary) is None:
            return []
        proc = _run([self.binary, "plugin", "--help"])
        if proc.returncode != 0:
            return []
        return [
            [
                self.binary,
                "plugin",
                "marketplace",
                "add",
                "rc-ventura/mcp-investidor10-wallet",
            ],
            [self.binary, "plugin", "add", "investidor10-carteira@investidor10"],
        ]

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            reg.name,
            "--",
            reg.command,
            *reg.args,
        ]


class GeminiAdapter(ClientAdapter):
    client_id = "gemini"
    binary = "gemini"
    label = "Gemini CLI"

    def plugin_install_commands(self) -> list[list[str]]:
        return [
            [
                self.binary,
                "extensions",
                "install",
                "https://github.com/rc-ventura/mcp-investidor10-wallet",
            ]
        ]

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            "-s",
            "user",
            reg.name,
            reg.command,
            *reg.args,
        ]


ADAPTERS = [ClaudeAdapter(), DevinAdapter(), CodexAdapter(), GeminiAdapter()]
