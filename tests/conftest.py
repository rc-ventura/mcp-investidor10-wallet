import os
import stat
import tempfile

import pytest

# Placeholder ID for offline tests; never a real wallet. Live tests (-m live)
# need a real public wallet passed explicitly: WALLET_ID=<id> uv run pytest -m live
PLACEHOLDER_WALLET_ID = "1234567"
os.environ.setdefault("WALLET_ID", PLACEHOLDER_WALLET_ID)
_test_dir = tempfile.mkdtemp(prefix="mcp-investidor10-tests-")
os.environ["WALLET_MEMORY_PATH"] = os.path.join(_test_dir, "memory.json")

from investidor10_wallet import privacy, setup_page, wallet_client


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """Keep every test away from the developer's real ~/.investidor10."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(privacy, "_configured", False)
    for client in (wallet_client.wallet_client, wallet_client.rest_client):
        monkeypatch.setattr(client, "wallet_id", client.wallet_id)
        monkeypatch.setattr(client, "share_hash", client.share_hash)
    yield home
    setup_page.close()


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
            'if [ "$1" = "plugin" ] && [ "$2" = "list" ]; then\n'
            f'  [ -f "{bin_dir}/plugin-list.out" ] && cat "{bin_dir}/plugin-list.out"\n'
            "fi\n"
            'if [ "$1" = "plugin" ] && [ "$2" = "marketplace" ] && [ "$3" = "list" ]; then\n'
            f'  [ -f "{bin_dir}/marketplace-list.out" ] && cat "{bin_dir}/marketplace-list.out"\n'
            "fi\n"
            f'if [ -f "{bin_dir}/fail-plugin" ]; then\n'
            '  case "$*" in *plugin*|*plugins*|*extensions*) exit 1;; esac\n'
            "fi\n"
            f'if [ -f "{bin_dir}/exit-code" ]; then\n'
            f'  exit "$(cat "{bin_dir}/exit-code")"\n'
            "fi\n"
            "exit 0\n"
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bin_dir
