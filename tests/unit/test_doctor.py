import json
import os
import sys

import filelock
import httpx
import pytest
import respx

from investidor10_wallet import __version__, wallet_config
from investidor10_wallet.installer import doctor

PROBE = (
    "https://investidor10.com.br/wallet/api/proxy/wallet-app/summary/metrics/1234567"
)
WALLET_ID = "1234567"
HASH = "TESTHASH_abc-1"
STATUSES = {"ok", "warn", "fail"}

posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX-only: fake clients are /bin/sh scripts"
)


def _config(home, mode="public", mask=False):
    wallet_config.write_config(
        home,
        wallet_config.LocalConfig(
            wallet_id=WALLET_ID,
            share_hash=HASH if mode == "restricted" else None,
            mode=mode,
            mask_values=mask,
            validated_at="2026-11-10T10:00:00-03:00",
            source="configure",
        ),
    )


def _environ(home, **extra):
    environ = {"WALLET_MEMORY_PATH": str(home / ".investidor10" / "memory.json")}
    environ.update(extra)
    return environ


def _collect(home, **kwargs):
    kwargs.setdefault("environ", _environ(home))
    return {c.id: c for c in doctor.collect(home=home, **kwargs)}


def _uv_present(tmp_path, monkeypatch):
    bin_dir = tmp_path / "uv-bin"
    bin_dir.mkdir()
    for name in ("uv", "uvx"):
        path = bin_dir / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))


@pytest.fixture
def source_ok():
    with respx.mock:
        respx.get(PROBE).mock(return_value=httpx.Response(200))
        yield


def test_every_check_has_id_status_cause_and_an_action_unless_ok(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    checks = doctor.collect(home=isolated_home, environ=_environ(isolated_home))
    assert checks
    ids = [c.id for c in checks]
    assert len(ids) == len(set(ids))
    for check in checks:
        assert check.id
        assert check.status in STATUSES
        assert check.cause
        if check.status != "ok":
            assert check.action


def test_missing_runner_is_a_failure_with_the_install_action(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    monkeypatch.setenv("PATH", str(tmp_path))
    checks = _collect(isolated_home)
    assert checks["runner"].status == "fail"
    assert "uv" in checks["runner"].cause
    assert "INSTALACAO-DESKTOP" in checks["runner"].action


def test_runner_present_is_ok(isolated_home, tmp_path, monkeypatch, source_ok):
    _uv_present(tmp_path, monkeypatch)
    assert _collect(isolated_home)["runner"].status == "ok"


def test_missing_configuration_fails_and_points_to_configure(
    isolated_home, tmp_path, monkeypatch
):
    _uv_present(tmp_path, monkeypatch)
    checks = _collect(isolated_home)
    assert checks["config"].status == "fail"
    assert "configure" in checks["config"].action
    assert "wallet" not in checks


def test_invalid_link_in_the_configuration_fails(isolated_home, tmp_path, monkeypatch):
    _uv_present(tmp_path, monkeypatch)
    directory = isolated_home / ".investidor10"
    directory.mkdir(mode=0o700)
    (directory / "config.json").write_text('{"wallet_id": "abc"}', encoding="utf-8")
    checks = _collect(isolated_home)
    assert checks["config"].status == "fail"
    assert "inválid" in checks["config"].cause or "ilegível" in checks["config"].cause
    assert "configure" in checks["config"].action


def test_configuration_from_a_newer_version_is_reported(
    isolated_home, tmp_path, monkeypatch
):
    _uv_present(tmp_path, monkeypatch)
    directory = isolated_home / ".investidor10"
    directory.mkdir(mode=0o700)
    (directory / "config.json").write_text('{"version": 99}', encoding="utf-8")
    checks = _collect(isolated_home)
    assert checks["config"].status == "fail"
    assert "mais nova" in checks["config"].cause


def test_configuration_is_reported_with_mode_and_mask_only(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="restricted", mask=True)
    cause = _collect(isolated_home)["config"].cause
    assert "restrita" in cause
    assert "mascaramento ligado" in cause
    assert "credencial presente" in cause
    assert HASH not in cause
    assert WALLET_ID not in cause


def test_public_configuration_says_the_credential_is_absent(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="public")
    cause = _collect(isolated_home)["config"].cause
    assert "pública" in cause
    assert "credencial ausente" in cause


@posix_only
def test_configuration_readable_by_others_is_a_warning(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    os.chmod(isolated_home / ".investidor10" / "config.json", 0o644)
    checks = _collect(isolated_home)
    assert checks["config_permissions"].status == "warn"
    assert "chmod 600" in checks["config_permissions"].action


@respx.mock
def test_wallet_with_denied_access_fails(isolated_home, tmp_path, monkeypatch):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="restricted")
    respx.get(PROBE).mock(return_value=httpx.Response(301))
    checks = _collect(isolated_home)
    assert checks["wallet"].status == "fail"
    assert "recusou" in checks["wallet"].cause
    assert "link" in checks["wallet"].action


@respx.mock
def test_private_public_wallet_fails_with_the_privacy_hint(
    isolated_home, tmp_path, monkeypatch
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="public")
    respx.get(PROBE).mock(return_value=httpx.Response(403))
    checks = _collect(isolated_home)
    assert checks["wallet"].status == "fail"
    assert "privada" in checks["wallet"].cause


@respx.mock
def test_missing_wallet_fails(isolated_home, tmp_path, monkeypatch):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    respx.get(PROBE).mock(return_value=httpx.Response(404))
    assert _collect(isolated_home)["wallet"].status == "fail"


@respx.mock
def test_source_down_is_a_warning_not_a_failure(isolated_home, tmp_path, monkeypatch):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    respx.get(PROBE).mock(return_value=httpx.Response(503))
    assert _collect(isolated_home)["wallet"].status == "warn"


def test_valid_wallet_is_ok(isolated_home, tmp_path, monkeypatch, source_ok):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    assert _collect(isolated_home)["wallet"].status == "ok"


@respx.mock
def test_restricted_wallet_answering_without_the_credential_warns_it_is_public(
    isolated_home, tmp_path, monkeypatch
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="restricted")
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    check = _collect(isolated_home)["restricted_exposure"]
    assert check.status == "warn"
    assert "indexável" in check.cause


@respx.mock
def test_restricted_wallet_refusing_without_the_credential_is_ok(
    isolated_home, tmp_path, monkeypatch
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="restricted")

    def answer(request):
        if request.url.params.get("hash"):
            return httpx.Response(200)
        return httpx.Response(301)

    respx.get(PROBE).mock(side_effect=answer)
    checks = _collect(isolated_home)
    assert checks["wallet"].status == "ok"
    assert checks["restricted_exposure"].status == "ok"


def test_public_wallet_has_no_exposure_check(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    assert "restricted_exposure" not in _collect(isolated_home)


@posix_only
def test_memory_without_write_permission_fails(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    directory = isolated_home / ".investidor10"
    os.chmod(directory, 0o500)
    try:
        checks = _collect(isolated_home)
    finally:
        os.chmod(directory, 0o700)
    assert checks["memory"].status == "fail"
    assert "escrita" in checks["memory"].cause
    assert "~" in checks["memory"].cause
    assert str(isolated_home) not in checks["memory"].cause


def test_memory_writable_and_lock_available_are_ok(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    checks = _collect(isolated_home)
    assert checks["memory"].status == "ok"
    assert checks["memory_lock"].status == "ok"


def test_memory_lock_held_by_another_process_is_a_warning(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    lock_path = isolated_home / ".investidor10" / "memory.json.lock"
    with filelock.FileLock(str(lock_path), fallback_to_soft=False):
        checks = _collect(isolated_home, lock_timeout=0.2)
    assert checks["memory_lock"].status == "warn"


def test_doctor_never_reads_or_prints_the_memory_content(
    isolated_home, tmp_path, monkeypatch, source_ok, capsys
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    memory = isolated_home / ".investidor10" / "memory.json"
    memory.write_text('{"theses": [{"text": "SEGREDO_TESE"}]}', encoding="utf-8")
    monkeypatch.setenv("WALLET_MEMORY_PATH", str(memory))
    doctor.run([])
    out = capsys.readouterr()
    assert "SEGREDO_TESE" not in out.out + out.err


@posix_only
def test_no_client_registered_anywhere_fails(
    isolated_home, fake_bin_dir, source_ok, monkeypatch
):
    _config(isolated_home)
    checks = _collect(isolated_home)
    assert checks["clients"].status == "fail"
    assert "install" in checks["clients"].action


@posix_only
def test_no_cli_detected_is_a_warning_that_admits_the_desktop_blind_spot(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    check = _collect(isolated_home)["clients"]
    assert check.status == "warn"
    assert "Claude Desktop" in check.cause


@posix_only
def test_plugin_server_in_claude_code_is_ok(
    isolated_home, fake_bin_dir, source_ok, monkeypatch
):
    _config(isolated_home)
    (fake_bin_dir / "mcp-list.out").write_text(
        "plugin:investidor10-carteira:carteira: uvx --from x - Connected\n"
    )
    (fake_bin_dir / "plugin-list.out").write_text(
        f"investidor10-carteira@investidor10\n  Version: {__version__}\n"
    )
    checks = _collect(isolated_home)
    assert checks["clients"].status == "ok"
    assert checks["versions"].status == "ok"
    assert "duplicate" not in checks or checks["duplicate"].status == "ok"


@posix_only
def test_synced_plugin_is_detected(isolated_home, fake_bin_dir, source_ok):
    _config(isolated_home)
    (fake_bin_dir / "plugin-list.out").write_text(
        f"investidor10-carteira@synced\n  Version: {__version__}\n"
    )
    check = _collect(isolated_home)["clients"]
    assert check.status == "ok"
    assert "sincroniz" in check.cause


@posix_only
def test_server_registered_twice_is_a_duplication_warning(
    isolated_home, fake_bin_dir, source_ok
):
    _config(isolated_home)
    (fake_bin_dir / "mcp-list.out").write_text(
        "carteira: uvx mcp-investidor10-wallet - Connected\n"
        "plugin:investidor10-carteira:carteira: uvx --from x - Connected\n"
    )
    (fake_bin_dir / "plugin-list.out").write_text(
        f"investidor10-carteira@investidor10\n  Version: {__version__}\n"
    )
    check = _collect(isolated_home)["duplicate"]
    assert check.status == "warn"
    assert "mcp remove carteira" in check.action


@posix_only
def test_plugin_version_different_from_the_package_is_a_warning(
    isolated_home, fake_bin_dir, source_ok
):
    _config(isolated_home)
    (fake_bin_dir / "mcp-list.out").write_text(
        "plugin:investidor10-carteira:carteira: uvx --from x - Connected\n"
    )
    (fake_bin_dir / "plugin-list.out").write_text(
        "investidor10-carteira@investidor10\n  Version: 0.1.1\n"
    )
    check = _collect(isolated_home)["versions"]
    assert check.status == "warn"
    assert "0.1.1" in check.cause
    assert __version__ in check.cause


def test_old_manual_entry_in_claude_desktop_config_is_a_warning(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    target = (
        isolated_home / "Library" / "Application Support" / "Claude"
    ) / "claude_desktop_config.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "carteira": {
                        "command": "uvx",
                        "args": ["mcp-investidor10-wallet"],
                        "env": {"WALLET_ID": WALLET_ID},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    check = _collect(isolated_home, platform_name="darwin")["desktop_manual_entry"]
    assert check.status == "warn"
    assert "~/Library/Application Support/Claude" in check.cause
    assert str(isolated_home) not in check.cause
    assert WALLET_ID not in check.cause + check.action


def test_desktop_config_without_the_product_is_ok(
    isolated_home, tmp_path, monkeypatch, source_ok
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    target = (
        isolated_home / "Library" / "Application Support" / "Claude"
    ) / "claude_desktop_config.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"mcpServers": {"outro": {}}}), encoding="utf-8")
    assert (
        _collect(isolated_home, platform_name="darwin")["desktop_manual_entry"].status
        == "ok"
    )


def test_exit_code_is_zero_without_failures(
    isolated_home, tmp_path, monkeypatch, source_ok, capsys
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    assert doctor.run([]) == 0
    assert "[falha]" not in capsys.readouterr().out


def test_exit_code_is_one_with_a_failure(isolated_home, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert doctor.run([]) == 1
    assert "falha" in capsys.readouterr().out.lower()


def test_output_names_cause_and_action_in_portuguese(
    isolated_home, tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("PATH", str(tmp_path))
    doctor.run([])
    out = capsys.readouterr().out
    assert "causa:" in out
    assert "ação:" in out
    assert "runner" in out


@respx.mock
def test_output_has_no_id_credential_home_or_user_name(
    isolated_home, tmp_path, monkeypatch, capsys
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home, mode="restricted", mask=True)
    respx.get(PROBE).mock(return_value=httpx.Response(200))
    monkeypatch.setenv(
        "WALLET_MEMORY_PATH", str(isolated_home / ".investidor10" / "memory.json")
    )
    doctor.run([])
    out = capsys.readouterr()
    text = out.out + out.err
    assert WALLET_ID not in text
    assert HASH not in text
    assert str(isolated_home) not in text
    assert isolated_home.name not in text.replace("~", "")
    assert "R$" not in text


def test_sanitize_scrubs_secrets_that_slip_into_a_message(tmp_path):
    home = tmp_path / "pessoa"
    raw = f"erro em {home}/x com {WALLET_ID} e {HASH} de pessoa"
    clean = doctor.sanitize(raw, home=home, secrets=[WALLET_ID, HASH])
    assert str(home) not in clean
    assert WALLET_ID not in clean
    assert HASH not in clean
    assert "pessoa" not in clean
    assert "~/x" in clean


def test_issue_block_summarises_without_sensitive_data(
    isolated_home, tmp_path, monkeypatch, source_ok, capsys
):
    _uv_present(tmp_path, monkeypatch)
    _config(isolated_home)
    doctor.run([])
    out = capsys.readouterr().out
    assert "cole abaixo" in out.lower()
    assert __version__ in out
