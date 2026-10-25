import shutil
import subprocess

from . import SERVER_ALIAS, ClientRegistration, RegisterOutcome

RUNNER_COMMAND = "uvx"
RUNNER_ARGS = ["mcp-investidor10-wallet"]


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=False, capture_output=True, text=True)


class ClientAdapter:
    client_id = ""
    binary = ""
    label = ""

    def detect(self) -> bool:
        return shutil.which(self.binary) is not None

    def list_existing(self) -> bool:
        proc = _run([self.binary, "mcp", "list"])
        return SERVER_ALIAS in proc.stdout

    def add_command(self, reg: ClientRegistration) -> list[str]:
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

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            reg.name,
            "--scope",
            "user",
            "--",
            "env",
            f"WALLET_ID={reg.env['WALLET_ID']}",
            reg.command,
            *reg.args,
        ]


class DevinAdapter(ClientAdapter):
    client_id = "devin"
    binary = "devin"
    label = "Devin CLI"

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            "-s",
            "user",
            reg.name,
            "-e",
            f"WALLET_ID={reg.env['WALLET_ID']}",
            "--",
            reg.command,
            *reg.args,
        ]


class CodexAdapter(ClientAdapter):
    client_id = "codex"
    binary = "codex"
    label = "Codex"

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            reg.name,
            "--env",
            f"WALLET_ID={reg.env['WALLET_ID']}",
            "--",
            reg.command,
            *reg.args,
        ]


class GeminiAdapter(ClientAdapter):
    client_id = "gemini"
    binary = "gemini"
    label = "Gemini CLI"

    def add_command(self, reg: ClientRegistration) -> list[str]:
        return [
            self.binary,
            "mcp",
            "add",
            "-s",
            "user",
            "-e",
            f"WALLET_ID={reg.env['WALLET_ID']}",
            reg.name,
            reg.command,
            *reg.args,
        ]


ADAPTERS = [ClaudeAdapter(), DevinAdapter(), CodexAdapter(), GeminiAdapter()]
