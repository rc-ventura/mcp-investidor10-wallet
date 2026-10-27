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
def test_success_registers_all_detected_and_installs_plugin_by_default(
    fake_bin_dir, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567"]) == 0
    log = (fake_bin_dir / "calls.log").read_text()
    for client in ("claude", "codex"):
        assert f"{client} mcp add carteira" in log
    assert "devin mcp add -s user carteira -e WALLET_ID=1234567" in log
    assert "gemini mcp add -s user -e WALLET_ID=1234567 carteira" in log
    assert "claude plugin marketplace add rc-ventura/mcp-investidor10-wallet" in log
    assert "devin plugins install rc-ventura/mcp-investidor10-wallet#plugin -y" in log
    assert "codex plugin add investidor10-carteira@investidor10" in log
    assert "gemini extensions install" in log
    out = capsys.readouterr().out
    assert "carteira" in out
    assert "plugin" in out


@respx.mock
def test_mcp_only_flag_skips_plugin_install(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--mcp-only"]) == 0
    log = (fake_bin_dir / "calls.log").read_text()
    assert "claude mcp add carteira" in log
    assert "plugin marketplace" not in log
    assert "plugins install" not in log
    assert "extensions install" not in log


@respx.mock
def test_dry_run_reports_simulation_and_registers_nothing(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "SIMULAÇÃO (nenhuma configuração foi alterada)" in out
    assert "instalaria o plugin" in out
    log = fake_bin_dir / "calls.log"
    assert "mcp add" not in (log.read_text() if log.exists() else "")


@respx.mock
def test_yes_does_not_suppress_collision_prompt(fake_bin_dir, monkeypatch, capsys):
    (fake_bin_dir / "mcp-list.out").write_text("carteira\n")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "")
    assert cli.run(["--wallet-id", "1234567", "--yes", "--mcp-only"]) == 0
    assert asked
    assert "mantido" in capsys.readouterr().out


@respx.mock
def test_exit_4_when_all_registrations_fail(fake_bin_dir):
    (fake_bin_dir / "exit-code").write_text("1")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--mcp-only"]) == 4


@respx.mock
def test_invalid_clients_flag_aborts_pt_br(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--clients", "claude,foo"]) == 2
    assert "Clientes inválidos" in capsys.readouterr().err


@respx.mock
def test_wallet_id_must_be_digits(fake_bin_dir, capsys):
    assert cli.run(["--wallet-id", "1234567/../../../other", "--mcp-only"]) == 3
    assert "apenas números" in capsys.readouterr().err


@respx.mock
def test_absent_client_reported_when_explicitly_requested(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("PATH", str(_uv_only_dir(tmp_path)))
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--clients", "gemini", "--mcp-only"]) == 1
    assert "não encontrado" in capsys.readouterr().err


@respx.mock
def test_plugin_failure_does_not_change_exit_code(fake_bin_dir, capsys):
    (fake_bin_dir / "fail-plugin").write_text("")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567"]) == 0
    assert "falha ao instalar o plugin" in capsys.readouterr().out


@respx.mock
def test_wallet_prompt_eof_returns_pt_br_guidance(fake_bin_dir, monkeypatch, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))

    def boom(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", boom)
    assert cli.run(["--mcp-only"]) == 3
    assert "não-interativa" in capsys.readouterr().err
