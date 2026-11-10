import json
import sys

import httpx
import pytest
import respx

from investidor10_wallet.installer import cli

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX-only: fake clients are /bin/sh scripts"
)

PROBE = (
    "https://investidor10.com.br/wallet/api/proxy/wallet-app/summary/metrics/1234567"
)
HASH = "TESTHASH_abc-1"
RESTRICTED_LINK = f"https://investidor10.com.br/wallet/public/1234567?h={HASH}"
PUBLIC_LINK = "https://investidor10.com.br/carteira/1234567"


@pytest.fixture(autouse=True)
def no_terminal(monkeypatch):
    def end_of_input(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", end_of_input)


def answers(monkeypatch, *values):
    asked = []
    pending = list(values)

    def fake_input(prompt=""):
        asked.append(prompt)
        if not pending:
            raise EOFError
        return pending.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    return asked


def saved_config(home):
    path = home / ".investidor10" / "config.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


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
def test_exit_3_when_wallet_not_found(fake_bin_dir, isolated_home, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(404))
    assert cli.run(["--wallet-id", "1234567"]) == 3
    assert "carteira" in capsys.readouterr().err
    assert saved_config(isolated_home) is None


@respx.mock
def test_exit_1_when_no_client_detected(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PATH", str(_uv_only_dir(tmp_path)))
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask"]) == 1
    assert "Nenhum cliente" in capsys.readouterr().err


@respx.mock
def test_success_registers_all_detected_and_installs_plugin_by_default(
    fake_bin_dir, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask"]) == 0
    log = (fake_bin_dir / "calls.log").read_text()
    assert "codex mcp add carteira" in log
    assert "claude mcp add" not in log
    assert "devin mcp add -s user carteira --" in log
    assert "gemini mcp add -s user carteira uvx" in log
    assert "claude plugin marketplace add rc-ventura/mcp-investidor10-wallet" in log
    assert "devin plugins install rc-ventura/mcp-investidor10-wallet#plugin -y" in log
    assert "codex plugin add investidor10-carteira@investidor10" in log
    assert "gemini extensions install" in log
    out = capsys.readouterr().out
    assert "carteira" in out
    assert "plugin" in out


@respx.mock
def test_no_client_registration_carries_the_wallet_or_the_credential(fake_bin_dir):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--link", RESTRICTED_LINK, "--no-mask"]) == 0
    log = (fake_bin_dir / "calls.log").read_text()
    assert "WALLET_ID" not in log
    assert HASH not in log
    assert "1234567" not in log
    assert " -e " not in log and "--env" not in log


@respx.mock
def test_every_client_runs_the_installer_release_pinned(fake_bin_dir):
    from investidor10_wallet import __version__

    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--mcp-only"]) == 0
    registrations = [
        line
        for line in (fake_bin_dir / "calls.log").read_text().splitlines()
        if "mcp add" in line
    ]
    assert len(registrations) == 4
    for line in registrations:
        assert line.endswith(f"uvx mcp-investidor10-wallet@{__version__}")


@respx.mock
def test_mcp_only_flag_skips_plugin_install(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--mcp-only"]) == 0
    log = (fake_bin_dir / "calls.log").read_text()
    assert "claude mcp add carteira" in log
    assert "plugin marketplace" not in log
    assert "plugins install" not in log
    assert "extensions install" not in log


@respx.mock
def test_dry_run_reports_simulation_and_registers_nothing(
    fake_bin_dir, isolated_home, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "SIMULAÇÃO (nenhuma configuração foi alterada)" in out
    assert "instalaria o plugin" in out
    log = fake_bin_dir / "calls.log"
    assert "mcp add" not in (log.read_text() if log.exists() else "")
    assert saved_config(isolated_home) is None


@respx.mock
def test_yes_does_not_suppress_collision_prompt(fake_bin_dir, monkeypatch, capsys):
    (fake_bin_dir / "mcp-list.out").write_text("carteira\n")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    asked = answers(monkeypatch, "")
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--yes", "--mcp-only"]) == 0
    assert asked
    assert "mantido" in capsys.readouterr().out


@respx.mock
def test_exit_4_when_all_registrations_fail(fake_bin_dir):
    (fake_bin_dir / "exit-code").write_text("1")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--mcp-only"]) == 4


@respx.mock
def test_invalid_clients_flag_aborts_pt_br(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert (
        cli.run(["--wallet-id", "1234567", "--no-mask", "--clients", "claude,foo"]) == 2
    )
    assert "Clientes inválidos" in capsys.readouterr().err


@respx.mock
def test_wallet_id_must_be_digits(fake_bin_dir, isolated_home, capsys):
    assert cli.run(["--wallet-id", "1234567/../../../other", "--mcp-only"]) == 2
    assert "Não reconheci" in capsys.readouterr().err
    assert saved_config(isolated_home) is None


@respx.mock
def test_absent_client_reported_when_explicitly_requested(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("PATH", str(_uv_only_dir(tmp_path)))
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert (
        cli.run(
            ["--wallet-id", "1234567", "--no-mask", "--clients", "gemini", "--mcp-only"]
        )
        == 1
    )
    assert "não encontrado" in capsys.readouterr().err


@respx.mock
def test_plugin_failure_does_not_change_exit_code(fake_bin_dir, capsys):
    (fake_bin_dir / "fail-plugin").write_text("")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask"]) == 0
    assert "falha ao instalar o plugin" in capsys.readouterr().out


def test_link_prompt_eof_returns_pt_br_guidance(fake_bin_dir, capsys):
    assert cli.run(["--mcp-only"]) == 2
    assert "não-interativa" in capsys.readouterr().err


@respx.mock
def test_final_report_points_to_the_privacy_doc(fake_bin_dir, capsys):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask"]) == 0
    assert (
        "Privacidade: veja https://github.com/rc-ventura/mcp-investidor10-wallet"
        "/blob/main/docs/PRIVACY.md" in capsys.readouterr().out
    )


@respx.mock
def test_restricted_link_is_validated_with_the_hash_and_saved(
    fake_bin_dir, isolated_home, capsys
):
    route = respx.get(PROBE).mock(return_value=httpx.Response(200))

    assert cli.run(["--link", RESTRICTED_LINK, "--mask", "--mcp-only"]) == 0

    assert route.calls.last.request.url.params["hash"] == HASH
    config = saved_config(isolated_home)
    assert config["wallet_id"] == "1234567"
    assert config["share_hash"] == HASH
    assert config["mode"] == "restricted"
    assert config["mask_values"] is True
    assert config["source"] == "installer"
    out = capsys.readouterr()
    assert "restrita" in out.out
    assert "privacidade" in out.out.lower()
    for text in (out.out, out.err):
        assert HASH not in text
        assert "1234567" not in text


@respx.mock
def test_saved_configuration_file_is_private(fake_bin_dir, isolated_home):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--link", RESTRICTED_LINK, "--no-mask", "--mcp-only"]) == 0
    path = isolated_home / ".investidor10" / "config.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


@respx.mock
def test_mask_question_is_asked_when_no_flag_is_given(
    fake_bin_dir, isolated_home, monkeypatch
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    asked = answers(monkeypatch, "s")

    assert cli.run(["--link", RESTRICTED_LINK, "--mcp-only"]) == 0

    assert len(asked) == 1
    assert "privacidade" in asked[0].lower()
    assert saved_config(isolated_home)["mask_values"] is True


@respx.mock
def test_mask_defaults_to_off_when_the_question_cannot_be_answered(
    fake_bin_dir, isolated_home
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--link", RESTRICTED_LINK, "--mcp-only"]) == 0
    assert saved_config(isolated_home)["mask_values"] is False


@respx.mock
def test_public_link_warns_about_indexing_and_recommends_restricted(
    fake_bin_dir, isolated_home, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))

    assert cli.run(["--link", PUBLIC_LINK, "--no-mask", "--mcp-only"]) == 0

    out = capsys.readouterr().out
    assert "indexada" in out or "indexável" in out
    assert "restrita" in out
    config = saved_config(isolated_home)
    assert config["mode"] == "public"
    assert config["share_hash"] is None


@respx.mock
def test_wallet_id_flag_is_a_public_link(fake_bin_dir, isolated_home):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--mcp-only"]) == 0
    config = saved_config(isolated_home)
    assert config["mode"] == "public"
    assert config["wallet_id"] == "1234567"


@respx.mock
def test_link_is_asked_when_no_flag_is_given(fake_bin_dir, isolated_home, monkeypatch):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    asked = answers(monkeypatch, RESTRICTED_LINK, "n")

    assert cli.run(["--mcp-only"]) == 0

    assert "link" in asked[0].lower()
    assert saved_config(isolated_home)["mode"] == "restricted"


@pytest.mark.parametrize("status", [301, 401, 403])
@respx.mock
def test_access_denied_does_not_save_and_exits_3(
    fake_bin_dir, isolated_home, capsys, status
):
    respx.get(PROBE).mock(return_value=httpx.Response(status))

    assert cli.run(["--link", RESTRICTED_LINK, "--no-mask", "--mcp-only"]) == 3

    assert saved_config(isolated_home) is None
    err = capsys.readouterr().err
    assert "recusou" in err
    assert HASH not in err
    log = fake_bin_dir / "calls.log"
    assert not log.exists() or "mcp add" not in log.read_text()


@respx.mock
def test_unavailable_source_asks_and_saves_only_on_yes(
    fake_bin_dir, isolated_home, monkeypatch
):
    respx.get(PROBE).mock(return_value=httpx.Response(503))
    asked = answers(monkeypatch, "s")

    assert cli.run(["--link", PUBLIC_LINK, "--no-mask", "--mcp-only"]) == 0

    assert "[s/N]" in asked[0]
    assert saved_config(isolated_home)["wallet_id"] == "1234567"


@respx.mock
def test_unavailable_source_declined_does_not_save(
    fake_bin_dir, isolated_home, monkeypatch
):
    respx.get(PROBE).mock(return_value=httpx.Response(503))
    answers(monkeypatch, "")

    assert cli.run(["--link", PUBLIC_LINK, "--no-mask", "--mcp-only"]) == 4

    assert saved_config(isolated_home) is None


@respx.mock
def test_yes_does_not_answer_the_unavailable_source_question(
    fake_bin_dir, isolated_home, monkeypatch
):
    respx.get(PROBE).mock(return_value=httpx.Response(503))
    asked = answers(monkeypatch, "n")

    code = cli.run(["--link", PUBLIC_LINK, "--no-mask", "--yes", "--mcp-only"])

    assert code == 4
    assert asked
    assert saved_config(isolated_home) is None


@respx.mock
def test_unavailable_source_without_a_terminal_does_not_save(
    fake_bin_dir, isolated_home
):
    respx.get(PROBE).mock(side_effect=httpx.ConnectTimeout("timed out"))
    assert cli.run(["--link", PUBLIC_LINK, "--no-mask", "--mcp-only"]) == 4
    assert saved_config(isolated_home) is None


# configure


def test_configure_does_not_need_the_runner(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert cli.run_configure([]) == 2
    assert "uv" not in capsys.readouterr().err


@respx.mock
def test_configure_redoes_link_and_mask_without_touching_any_client(
    fake_bin_dir, isolated_home, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))

    assert cli.run_configure(["--link", RESTRICTED_LINK, "--mask"]) == 0

    config = saved_config(isolated_home)
    assert config["source"] == "configure"
    assert config["mask_values"] is True
    assert config["mode"] == "restricted"
    log = fake_bin_dir / "calls.log"
    assert not log.exists() or log.read_text() == ""
    out = capsys.readouterr().out
    assert "restrita" in out
    assert HASH not in out


@respx.mock
def test_configure_mask_flag_changes_only_the_mask(fake_bin_dir, isolated_home):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run_configure(["--link", RESTRICTED_LINK, "--no-mask"]) == 0
    assert cli.run_configure(["--link", RESTRICTED_LINK, "--mask"]) == 0
    config = saved_config(isolated_home)
    assert config["mask_values"] is True
    assert config["share_hash"] == HASH


@respx.mock
def test_configure_twice_with_the_same_answers_leaves_the_file_untouched(
    fake_bin_dir, isolated_home, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    path = isolated_home / ".investidor10" / "config.json"
    assert cli.run_configure(["--link", RESTRICTED_LINK, "--mask"]) == 0
    before = (path.stat().st_mtime_ns, path.read_bytes())

    assert cli.run_configure(["--link", RESTRICTED_LINK, "--mask"]) == 0

    assert (path.stat().st_mtime_ns, path.read_bytes()) == before
    assert "inalterada" in capsys.readouterr().out


@respx.mock
def test_configure_asks_before_switching_to_another_wallet(
    fake_bin_dir, isolated_home, monkeypatch
):
    other_probe = PROBE.replace("1234567", "7654321")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    respx.get(other_probe).mock(return_value=httpx.Response(200))
    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 0
    asked = answers(monkeypatch, "s")

    code = cli.run_configure(
        ["--link", "https://investidor10.com.br/carteira/7654321", "--no-mask"]
    )

    assert code == 0
    assert "[s/N]" in asked[0]
    assert "memória" in asked[0]
    assert saved_config(isolated_home)["wallet_id"] == "7654321"


@respx.mock
def test_configure_keeps_the_current_wallet_when_the_switch_is_declined(
    fake_bin_dir, isolated_home, monkeypatch, capsys
):
    other_probe = PROBE.replace("1234567", "7654321")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    respx.get(other_probe).mock(return_value=httpx.Response(200))
    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 0
    answers(monkeypatch, "n")

    code = cli.run_configure(
        ["--link", "https://investidor10.com.br/carteira/7654321", "--no-mask"]
    )

    assert code == 0
    assert saved_config(isolated_home)["wallet_id"] == "1234567"
    assert "mantida" in capsys.readouterr().out


@respx.mock
def test_yes_does_not_answer_the_wallet_switch_question(
    fake_bin_dir, isolated_home, monkeypatch
):
    other_probe = PROBE.replace("1234567", "7654321")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    respx.get(other_probe).mock(return_value=httpx.Response(200))
    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 0

    code = cli.run_configure(
        [
            "--link",
            "https://investidor10.com.br/carteira/7654321",
            "--no-mask",
            "--yes",
        ]
    )

    assert code == 2
    assert saved_config(isolated_home)["wallet_id"] == "1234567"


@respx.mock
def test_configure_adding_a_credential_to_the_same_wallet_needs_no_confirmation(
    fake_bin_dir, isolated_home
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 0

    assert cli.run_configure(["--link", RESTRICTED_LINK, "--no-mask"]) == 0

    config = saved_config(isolated_home)
    assert config["mode"] == "restricted"
    assert config["share_hash"] == HASH


def test_configure_exit_2_for_an_invalid_link(isolated_home, capsys):
    assert cli.run_configure(["--link", "https://example.com/x"]) == 2
    assert "Investidor10" in capsys.readouterr().err
    assert saved_config(isolated_home) is None


@respx.mock
def test_configure_exit_3_for_access_denied_and_not_found(isolated_home):
    respx.get(PROBE).mock(return_value=httpx.Response(301))
    assert cli.run_configure(["--link", RESTRICTED_LINK, "--no-mask"]) == 3
    respx.get(PROBE).mock(return_value=httpx.Response(404))
    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 3
    assert saved_config(isolated_home) is None


@respx.mock
def test_configure_exit_4_for_an_unavailable_source_without_confirmation(
    isolated_home,
):
    respx.get(PROBE).mock(return_value=httpx.Response(500))
    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 4
    assert saved_config(isolated_home) is None


@respx.mock
def test_configure_refuses_to_overwrite_a_configuration_from_a_future_version(
    isolated_home, capsys
):
    path = isolated_home / ".investidor10" / "config.json"
    path.parent.mkdir(mode=0o700)
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    respx.get(PROBE).mock(return_value=httpx.Response(200))

    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 2

    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 99}
    assert "versão" in capsys.readouterr().err


@respx.mock
def test_configure_replaces_a_corrupted_configuration(isolated_home):
    path = isolated_home / ".investidor10" / "config.json"
    path.parent.mkdir(mode=0o700)
    path.write_text("{broken", encoding="utf-8")
    respx.get(PROBE).mock(return_value=httpx.Response(200))

    assert cli.run_configure(["--link", PUBLIC_LINK, "--no-mask"]) == 0

    assert saved_config(isolated_home)["wallet_id"] == "1234567"


def _claude_log(fake_bin_dir):
    log = fake_bin_dir / "calls.log"
    if not log.exists():
        return []
    return [line for line in log.read_text().splitlines() if line.startswith("claude ")]


@respx.mock
def test_claude_default_installs_the_plugin_pinned_and_does_not_register(
    fake_bin_dir, capsys
):
    from investidor10_wallet import __version__

    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--clients", "claude"]) == 0
    log = "\n".join(_claude_log(fake_bin_dir))
    assert (
        f"claude plugin marketplace add rc-ventura/mcp-investidor10-wallet#v{__version__}"
        in log
    )
    assert "claude plugin install investidor10-carteira@investidor10" in log
    assert "claude mcp add" not in log
    assert "vem com o plugin" in capsys.readouterr().out


@respx.mock
def test_claude_with_synced_plugin_explains_why_it_does_not_install(
    fake_bin_dir, capsys
):
    (fake_bin_dir / "plugin-list.out").write_text("investidor10-carteira@synced\n")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    assert cli.run(["--wallet-id", "1234567", "--no-mask", "--clients", "claude"]) == 0
    log = "\n".join(_claude_log(fake_bin_dir))
    assert "plugin install" not in log
    assert "Claude Desktop" in capsys.readouterr().out


@respx.mock
def test_claude_old_registration_asks_once_and_removes_only_on_yes(
    fake_bin_dir, monkeypatch, isolated_home
):
    (fake_bin_dir / "mcp-list.out").write_text("carteira: uvx x\n")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    asked = answers(monkeypatch, "s")
    args = ["--wallet-id", "1234567", "--no-mask", "--clients", "claude"]
    assert cli.run(args) == 0
    assert len([a for a in asked if "instalação anterior" in a]) == 1
    assert "claude mcp remove carteira -s user" in _claude_log(fake_bin_dir)


@respx.mock
def test_claude_old_registration_refused_installs_plugin_and_reports_duplication(
    fake_bin_dir, monkeypatch, isolated_home, capsys
):
    (fake_bin_dir / "mcp-list.out").write_text("carteira: uvx x\n")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    answers(monkeypatch, "")
    args = ["--wallet-id", "1234567", "--no-mask", "--clients", "claude"]
    assert cli.run(args) == 0
    log = "\n".join(_claude_log(fake_bin_dir))
    assert "mcp remove" not in log
    assert "plugin install" in log
    assert "duplic" in capsys.readouterr().out


@respx.mock
def test_mcp_only_in_claude_registers_the_server_and_warns_about_the_plugin(
    fake_bin_dir, capsys
):
    (fake_bin_dir / "plugin-list.out").write_text(
        "investidor10-carteira@investidor10\n"
    )
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    args = ["--wallet-id", "1234567", "--no-mask", "--clients", "claude", "--mcp-only"]
    assert cli.run(args) == 0
    log = "\n".join(_claude_log(fake_bin_dir))
    assert "claude mcp add carteira" in log
    assert "plugin install" not in log
    assert "duplic" in capsys.readouterr().out


@respx.mock
def test_dry_run_in_claude_announces_the_plugin_and_runs_nothing(
    fake_bin_dir, isolated_home, capsys
):
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    args = ["--wallet-id", "1234567", "--no-mask", "--clients", "claude", "--dry-run"]
    assert cli.run(args) == 0
    assert "instalaria o plugin" in capsys.readouterr().out
    assert not any("plugin install" in line for line in _claude_log(fake_bin_dir))
