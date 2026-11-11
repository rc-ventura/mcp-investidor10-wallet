import pytest

from investidor10_wallet import server
from investidor10_wallet.installer import cli, doctor


def test_main_dispatches_install_subcommand_without_starting_server(monkeypatch):
    """install dispatch must call the assistant with the remaining args and exit."""
    calls = []
    monkeypatch.setattr(cli, "run", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(
        server.sys, "argv", ["mcp-investidor10-wallet", "install", "--dry-run"]
    )

    with pytest.raises(SystemExit) as exc_info:
        server.main()

    assert exc_info.value.code == 0
    assert calls == [["--dry-run"]]


def test_main_keeps_server_path_for_other_argv(monkeypatch):
    """any argv without 'install' must follow the existing server path untouched."""
    calls = []
    monkeypatch.setattr(cli, "run", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(server.sys, "argv", ["mcp-investidor10-wallet"])

    class Sentinel(Exception):
        pass

    def fail_load_config():
        raise Sentinel()

    monkeypatch.setattr(server.bootstrap, "load_config", fail_load_config)

    with pytest.raises(Sentinel):
        server.main()

    assert calls == []


def test_main_dispatches_configure_subcommand_without_starting_server(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_configure", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(
        server.sys, "argv", ["mcp-investidor10-wallet", "configure", "--mask"]
    )

    with pytest.raises(SystemExit) as exc_info:
        server.main()

    assert exc_info.value.code == 0
    assert calls == [["--mask"]]


def test_main_does_not_send_configure_to_the_install_assistant(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(cli, "run_configure", lambda argv: 0)
    monkeypatch.setattr(server.sys, "argv", ["mcp-investidor10-wallet", "configure"])

    with pytest.raises(SystemExit):
        server.main()

    assert calls == []


def test_main_dispatches_doctor_subcommand_without_starting_server(monkeypatch):
    calls = []
    monkeypatch.setattr(doctor, "run", lambda argv: calls.append(argv) or 1)
    monkeypatch.setattr(server.sys, "argv", ["mcp-investidor10-wallet", "doctor"])

    with pytest.raises(SystemExit) as exc_info:
        server.main()

    assert exc_info.value.code == 1
    assert calls == [[]]
