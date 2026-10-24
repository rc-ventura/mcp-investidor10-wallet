import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from investidor10_wallet import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_entry_point_is_importable():
    from investidor10_wallet.server import main

    assert callable(main)


def test_version_matches_pyproject():
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    assert pyproject["project"]["dynamic"] == ["version"]
    assert __version__ == "0.1.0"


def test_console_script_points_to_main():
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    scripts = pyproject["project"]["scripts"]
    assert scripts["mcp-investidor10-wallet"] == "investidor10_wallet.server:main"


def test_wheel_target_exports_only_package_namespace():
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    wheel_packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert wheel_packages == ["src/investidor10_wallet"]
    for top_level in ("server.py", "wallet_client.py", "memory_store.py"):
        assert not (PROJECT_ROOT / top_level).exists()


def test_server_main_serves_stdio_initialize_handshake(tmp_path):
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "packaging-contract-test", "version": "0.1.0"},
        },
    }
    env = {
        **os.environ,
        "WALLET_ID": "1234567",
        "HOME": str(tmp_path),
        "WALLET_MEMORY_PATH": str(tmp_path / "memory.json"),
        "HTTPS_PROXY": "http://127.0.0.1:1",
        "HTTP_PROXY": "http://127.0.0.1:1",
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "investidor10_wallet.server"],
        input=json.dumps(init_request) + "\n",
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, (
        f"expected JSON-RPC response on stdout, got empty (stderr={proc.stderr!r})"
    )
    response = json.loads(lines[0])
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "investidor10-wallet"
