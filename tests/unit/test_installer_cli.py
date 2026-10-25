import httpx
import respx

from investidor10_wallet.installer import cli

PROBE = (
    "https://investidor10.com.br/wallet/api/proxy/wallet-app/summary/metrics/1234567"
)


def _uv_only_dir(tmp_path):
    bin_dir = tmp_path / "uv-only"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text("#!/bin/sh\nexit 0\n")
    uv.chmod(0o755)
    return bin_dir


def test_exit_2_when_runner_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert cli.run(["--wallet-id", "1234567"]) == 2
    assert "uv" in capsys.readouterr().err


@respx.mock
def test_exit_3_when_wallet_not_found(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(404))
    assert cli.run(["--wallet-id", "1234567"]) == 3
    assert "carteira" in capsys.readouterr().err


@respx.mock
def test_exit_1_when_no_client_detected(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PATH", str(_uv_only_dir(tmp_path)))
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567"]) == 1
    assert "Nenhum cliente" in capsys.readouterr().err


@respx.mock
def test_success_registers_all_detected(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567"]) == 0
    log = (fake_bin_dir / "calls.log").read_text()
    for client in ("claude", "codex"):
        assert f"{client} mcp add carteira" in log
    assert "devin mcp add -s user carteira -e WALLET_ID=1234567" in log
    assert "gemini mcp add -s user -e WALLET_ID=1234567 carteira" in log
    assert "carteira" in capsys.readouterr().out


@respx.mock
def test_dry_run_reports_simulation_and_registers_nothing(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "SIMULAÇÃO (nenhuma configuração foi alterada)" in out
    log = fake_bin_dir / "calls.log"
    assert "mcp add" not in (log.read_text() if log.exists() else "")


@respx.mock
def test_yes_does_not_suppress_collision_prompt(fake_bin_dir, monkeypatch, capsys):
    (fake_bin_dir / "mcp-list.out").write_text("carteira\n")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "")
    assert cli.run(["--wallet-id", "1234567", "--yes"]) == 0
    assert asked
    assert "mantido" in capsys.readouterr().out


@respx.mock
def test_plugin_flag_prints_marketplace_instructions(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--plugin"]) == 0
    out = capsys.readouterr().out
    assert "claude plugin marketplace add rc-ventura/mcp-investidor10-wallet" in out


@respx.mock
def test_exit_4_when_all_registrations_fail(fake_bin_dir):
    (fake_bin_dir / "exit-code").write_text("1")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567"]) == 4
