import os
import stat
import tempfile

import pytest

os.environ.setdefault("WALLET_ID", "1234567")
_test_dir = tempfile.mkdtemp(prefix="mcp-investidor10-tests-")
os.environ["WALLET_MEMORY_PATH"] = os.path.join(_test_dir, "memory.json")


@pytest.fixture
def fake_bin_dir(tmp_path, monkeypatch):
    """Create fake claude/devin/gemini/uv executables that log every invocation."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    log_path = bin_dir / "calls.log"
    for name in ("claude", "devin", "codex", "gemini", "uv"):
        script = bin_dir / name
        script.write_text(
            "#!/bin/sh\n"
            f'echo "{name} $@" >> "{log_path}"\n'
            'if [ "$1" = "mcp" ] && [ "$2" = "list" ]; then\n'
            f'  [ -f "{bin_dir}/mcp-list.out" ] && cat "{bin_dir}/mcp-list.out"\n'
            "fi\n"
            "exit 0\n"
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bin_dir
