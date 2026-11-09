#!/usr/bin/env python3
import argparse
import json
import locale
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SERVER_NAME = "investidor10-wallet"
PROTOCOL_VERSION = "2025-03-26"
TIMEOUT_SECONDS = 120
REMOVED_VARIABLES = ("WALLET_ID", "WALLET_HASH", "WALLET_MEMORY_PATH")


def _fail(message: str) -> int:
    print(f"smoke_mcp: {message}", file=sys.stderr)
    return 1


def _child_env(home: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in REMOVED_VARIABLES}
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["HTTPS_PROXY"] = "http://127.0.0.1:1"
    env["HTTP_PROXY"] = "http://127.0.0.1:1"
    return env


def _requests() -> str:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "release-smoke", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    return "".join(json.dumps(message) + "\n" for message in messages)


def _responses(process: subprocess.Popen) -> dict:
    found: dict = {}
    for line in process.stdout:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if isinstance(message, dict) and message.get("id") in (1, 2):
            found[message["id"]] = message
        if len(found) == 2:
            break
    return found


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # on Windows the child writes stderr in the console code page
        return raw.decode(locale.getpreferredencoding(False), errors="replace")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Sobe o servidor MCP sem carteira e confere initialize e tools/list."
    )
    parser.add_argument("--expected-tools", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        return _fail("informe o comando do servidor depois de --.")

    with (
        tempfile.TemporaryDirectory(prefix="smoke-home-") as home,
        tempfile.TemporaryFile() as errors,
    ):
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                encoding="utf-8",
                env=_child_env(Path(home)),
            )
        except OSError as exc:
            return _fail(f"não foi possível iniciar o servidor: {exc}")
        timer = threading.Timer(TIMEOUT_SECONDS, process.kill)
        timer.start()
        try:
            process.stdin.write(_requests())
            process.stdin.flush()
            found = _responses(process)
        except OSError:
            found = {}
        finally:
            timer.cancel()
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()
        errors.seek(0)
        stderr = _decode(errors.read())

        if 1 not in found or 2 not in found:
            return _fail(
                "o servidor não respondeu ao initialize e ao tools/list. "
                f"stderr: {stderr.strip()}"
            )
        name = found[1].get("result", {}).get("serverInfo", {}).get("name")
        if name != SERVER_NAME:
            return _fail(f"serverInfo.name é {name!r}, esperado {SERVER_NAME!r}.")
        tools = found[2].get("result", {}).get("tools", [])
        if len(tools) != args.expected_tools:
            return _fail(
                f"o servidor expõe {len(tools)} tools, esperado {args.expected_tools}."
            )
        if not (Path(home) / ".investidor10").is_dir():
            return _fail("o servidor não criou o diretório ~/.investidor10.")
    print(f"smoke_mcp: initialize ok, {len(tools)} tools, servidor sem carteira.")
    if stderr.strip():
        print(f"smoke_mcp: stderr do servidor:\n{stderr.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
