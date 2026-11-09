import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "smoke_mcp.py"


def _run(*args, extra_env=None):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=60,
    )


def test_the_server_starts_without_a_wallet_and_lists_twenty_tools():
    result = _run(
        "--expected-tools",
        "20",
        "--",
        sys.executable,
        "-m",
        "investidor10_wallet.server",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "20 tools" in result.stdout


def test_a_wrong_tool_count_fails():
    result = _run(
        "--expected-tools",
        "19",
        "--",
        sys.executable,
        "-m",
        "investidor10_wallet.server",
    )
    assert result.returncode == 1
    assert "19" in result.stderr


def test_a_command_that_is_not_an_mcp_server_fails():
    result = _run("--expected-tools", "20", "--", sys.executable, "-c", "print('no')")
    assert result.returncode == 1


def test_the_child_never_sees_a_wallet_or_the_real_home(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import os, sys\n"
        "sys.stderr.write(repr((os.environ.get('WALLET_ID'), os.environ['HOME'])))\n",
        encoding="utf-8",
    )
    env_home = os.environ["HOME"]
    result = _run("--expected-tools", "20", "--", sys.executable, str(probe))
    assert result.returncode == 1
    assert "None" in result.stderr
    assert env_home not in result.stderr


def test_stderr_in_a_non_utf8_code_page_does_not_crash_the_script(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import sys\nsys.stderr.buffer.write(b'Aviso: n\\xe3o foi poss\\xedvel')\n",
        encoding="utf-8",
    )
    result = _run("--expected-tools", "20", "--", sys.executable, str(probe))
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "Aviso: n" in result.stderr


FAKE_SERVER = """
import json, os, sys
from pathlib import Path
(Path(os.environ["HOME"]) / ".investidor10").mkdir()
sys.stderr.buffer.write(b"Aviso: n\\xe3o foi poss\\xedvel restringir\\n")
sys.stderr.flush()
tools = [{"name": f"t{i}", "inputSchema": {"type": "object"}} for i in range(20)]
for line in sys.stdin:
    message = json.loads(line)
    if message.get("id") == 1:
        result = {"serverInfo": {"name": "investidor10-wallet"}, "capabilities": {}}
    elif message.get("id") == 2:
        result = {"tools": tools}
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
"""


def test_a_passing_run_prints_a_non_utf8_stderr_on_a_cp1252_console(tmp_path):
    server = tmp_path / "fake_server.py"
    server.write_text(FAKE_SERVER, encoding="utf-8")

    result = _run(
        "--expected-tools",
        "20",
        "--",
        sys.executable,
        str(server),
        extra_env={"PYTHONIOENCODING": "cp1252"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "stderr do servidor" in result.stdout
    assert "Aviso: n" in result.stdout
