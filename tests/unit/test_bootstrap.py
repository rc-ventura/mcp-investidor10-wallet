import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import respx

from investidor10_wallet import bootstrap, server, wallet_client
from investidor10_wallet.memory_store import MemoryStore


def test_missing_wallet_id_aborts_with_pt_br_message():
    with pytest.raises(SystemExit) as exc:
        bootstrap.load_config({})
    assert "WALLET_ID" in str(exc.value)
    assert "investidor10.com.br/carteira" in str(exc.value)


def test_blank_wallet_id_aborts_with_pt_br_message():
    with pytest.raises(SystemExit) as exc:
        bootstrap.load_config({"WALLET_ID": "   "})
    assert "WALLET_ID" in str(exc.value)


def test_non_numeric_wallet_id_aborts():
    with pytest.raises(SystemExit) as exc:
        bootstrap.load_config({"WALLET_ID": "abc123"})
    assert "WALLET_ID" in str(exc.value)


def test_unicode_digits_wallet_id_aborts():
    with pytest.raises(SystemExit) as exc:
        bootstrap.load_config({"WALLET_ID": "١٢٣"})
    assert "WALLET_ID" in str(exc.value)


def test_invalid_ttl_aborts_with_pt_br_message():
    with pytest.raises(SystemExit) as exc:
        bootstrap.load_config({"WALLET_ID": "123", "WALLET_CACHE_TTL_SECONDS": "abc"})
    assert "WALLET_CACHE_TTL_SECONDS" in str(exc.value)


def test_valid_config_returns_parsed_values():
    config = bootstrap.load_config(
        {
            "WALLET_ID": " 42 ",
            "WALLET_CACHE_TTL_SECONDS": "120",
            "WALLET_CACHE_MAX_STALE_SECONDS": "3600",
        }
    )
    assert config["wallet_id"] == "42"
    assert config["ttl_seconds"] == 120
    assert config["max_stale_seconds"] == 3600


def test_config_failure_makes_no_network_calls():
    with respx.mock(assert_all_called=False) as router:
        router.get(url__regex=r".*").mock(
            side_effect=AssertionError("no network call expected")
        )
        with pytest.raises(SystemExit):
            bootstrap.load_config({"WALLET_ID": "nope"})


def test_override_returns_custom_path_without_migration(tmp_path):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    legacy = cwd / "memory.json"
    legacy.write_text('{"version": 1}', encoding="utf-8")
    custom = tmp_path / "custom" / "mem.json"

    resolved = bootstrap.resolve_memory_path(
        cwd=cwd,
        home=home,
        environ={"WALLET_MEMORY_PATH": str(custom)},
    )

    assert resolved == str(custom)
    assert legacy.exists()
    assert not (home / ".investidor10").exists()


def test_novo_canonico_creates_canonical_dir_0700_and_first_save_persists(tmp_path):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()

    resolved = bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    canonical_dir = home / ".investidor10"
    canonical_file = canonical_dir / "memory.json"
    assert resolved == str(canonical_file)
    assert canonical_dir.is_dir()
    assert (canonical_dir.stat().st_mode & 0o777) == 0o700

    store = MemoryStore(resolved)
    assert store.available is True
    store.save_rule("comprar apenas ativos com lucro consistente")
    assert canonical_file.is_file()
    assert (canonical_file.stat().st_mode & 0o777) == 0o600
    reloaded = MemoryStore(resolved)
    assert len(reloaded.get_rules()) == 1


def test_migrado_copies_legacy_sets_0700_0600_removes_legacy_and_warns(
    tmp_path, capsys
):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    legacy = cwd / "memory.json"
    seed = MemoryStore(str(legacy))
    seed.save_thesis("PETR4", "geração de caixa")
    seed.save_rule("máximo 10% por ativo")
    original_bytes = legacy.read_bytes()

    resolved = bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    canonical = home / ".investidor10" / "memory.json"
    assert resolved == str(canonical)
    assert not legacy.exists()
    assert canonical.read_bytes() == original_bytes
    assert (canonical.parent.stat().st_mode & 0o777) == 0o700
    assert (canonical.stat().st_mode & 0o777) == 0o600
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(legacy) in captured.err
    assert str(canonical) in captured.err


def test_canonico_wins_keeps_canonical_renames_legacy_with_microseconds_and_warns(
    tmp_path, capsys
):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    canonical_dir = home / ".investidor10"
    cwd.mkdir()
    canonical_dir.mkdir(parents=True, mode=0o700)
    canonical = canonical_dir / "memory.json"
    legacy = cwd / "memory.json"
    canonical.write_text('{"version": 1, "source": "canonical"}', encoding="utf-8")
    legacy.write_text('{"version": 1, "source": "legacy"}', encoding="utf-8")
    fixed_now = datetime(2026, 10, 18, 14, 5, 6, 789012)

    resolved = bootstrap.resolve_memory_path(
        cwd=cwd, home=home, environ={}, now=fixed_now
    )

    assert resolved == str(canonical)
    assert (
        canonical.read_text(encoding="utf-8") == '{"version": 1, "source": "canonical"}'
    )
    assert not legacy.exists()
    backups = list(cwd.glob("memory.json.legacy-*"))
    assert len(backups) == 1
    assert re.fullmatch(
        r"memory\.json\.legacy-[0-9]{8}-[0-9]{6}-[0-9]{6}", backups[0].name
    )
    assert (
        backups[0].read_text(encoding="utf-8") == '{"version": 1, "source": "legacy"}'
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(canonical) in captured.err
    assert str(backups[0]) in captured.err


def test_cwd_equal_to_canonical_dir_does_not_conflict_with_itself(tmp_path, capsys):
    home = tmp_path / "home"
    canonical_dir = home / ".investidor10"
    canonical_dir.mkdir(parents=True, mode=0o700)
    canonical = canonical_dir / "memory.json"
    canonical.write_text('{"version": 1, "source": "same"}', encoding="utf-8")

    resolved = bootstrap.resolve_memory_path(cwd=canonical_dir, home=home, environ={})

    assert resolved == str(canonical)
    assert canonical.exists()
    assert canonical.read_text(encoding="utf-8") == '{"version": 1, "source": "same"}'
    assert list(canonical_dir.glob("memory.json.legacy-*")) == []
    assert capsys.readouterr().err == ""


def test_migration_failure_aborts_with_pt_br_and_keeps_legacy_intact(
    tmp_path, monkeypatch
):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    legacy = cwd / "memory.json"
    legacy.write_text('{"version": 1}', encoding="utf-8")
    monkeypatch.setattr(
        "investidor10_wallet.bootstrap.os.replace",
        lambda *_args: (_ for _ in ()).throw(OSError("permissão negada")),
    )

    with pytest.raises(SystemExit) as exc:
        bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    msg = str(exc.value)
    assert str(legacy) in msg
    assert str(home / ".investidor10" / "memory.json") in msg
    assert legacy.read_text(encoding="utf-8") == '{"version": 1}'


def test_migration_unlink_failure_aborts_with_pt_br_and_keeps_legacy(
    tmp_path, monkeypatch
):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    legacy = cwd / "memory.json"
    legacy.write_text('{"version": 1}', encoding="utf-8")
    orig_unlink = Path.unlink

    def fail_legacy_unlink(self, *args, **kwargs):
        if self == legacy:
            raise PermissionError("diretório somente leitura")
        return orig_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_legacy_unlink)

    with pytest.raises(SystemExit) as exc:
        bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    assert str(legacy) in str(exc.value)
    assert legacy.exists()
    assert not (home / ".investidor10" / "memory.json").exists()


def test_migration_rejects_symlinked_legacy_file(tmp_path):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    secret = tmp_path / "secret.json"
    secret.write_text('{"secret": true}', encoding="utf-8")
    legacy = cwd / "memory.json"
    legacy.symlink_to(secret)

    with pytest.raises(SystemExit):
        bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    assert secret.exists()
    assert not (home / ".investidor10" / "memory.json").exists()


def test_migration_rejects_symlinked_canonical_dir(tmp_path):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    other = tmp_path / "other"
    cwd.mkdir()
    home.mkdir()
    other.mkdir(mode=0o755)
    os.chmod(other, 0o755)
    (home / ".investidor10").symlink_to(other)

    with pytest.raises(SystemExit):
        bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    assert (other.stat().st_mode & 0o777) == 0o755


def test_migration_aborts_if_legacy_inode_changes_before_unlink(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    legacy = cwd / "memory.json"
    legacy.write_text('{"version": 1, "step": "initial"}', encoding="utf-8")
    real_atomic_copy = bootstrap._atomic_copy

    def copy_then_swap_legacy(source: Path, destination: Path):
        result = real_atomic_copy(source, destination)
        replacement = cwd / "replacement.json"
        replacement.write_text('{"version": 1, "step": "swapped"}', encoding="utf-8")
        os.replace(replacement, source)
        return result

    monkeypatch.setattr(bootstrap, "_atomic_copy", copy_then_swap_legacy)

    with pytest.raises(SystemExit):
        bootstrap.resolve_memory_path(cwd=cwd, home=home, environ={})

    assert legacy.exists()
    assert legacy.read_text(encoding="utf-8") == '{"version": 1, "step": "swapped"}'


@respx.mock
async def test_probe_200_succeeds_silently(capsys):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/2061045").mock(
        return_value=httpx.Response(200, json={"applied": 1, "equity": 1})
    )

    await wallet_client.validate_wallet("2061045")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@respx.mock
async def test_probe_404_aborts_with_not_found_or_private_pt_br():
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/99999").mock(
        return_value=httpx.Response(404)
    )

    with pytest.raises(SystemExit) as exc:
        await wallet_client.validate_wallet("99999")

    assert str(exc.value) == bootstrap.WALLET_NOT_FOUND_MESSAGE.format(
        wallet_id="99999"
    )


@pytest.mark.parametrize("status_code", [401, 403])
@respx.mock
async def test_probe_401_and_403_abort_with_private_pt_br(status_code):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/2061045").mock(
        return_value=httpx.Response(status_code)
    )

    with pytest.raises(SystemExit) as exc:
        await wallet_client.validate_wallet("2061045")

    assert str(exc.value) == bootstrap.WALLET_PRIVATE_MESSAGE.format(
        wallet_id="2061045"
    )


@pytest.mark.parametrize("status_code", [500, 502, 503, 429])
@respx.mock
async def test_probe_5xx_and_other_status_warns_and_continues(status_code, capsys):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/2061045").mock(
        return_value=httpx.Response(status_code)
    )

    await wallet_client.validate_wallet("2061045")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        bootstrap.PROBE_UNAVAILABLE_MESSAGE.format(wallet_id="2061045") in captured.err
    )


@respx.mock
async def test_probe_timeout_warns_on_stderr_and_continues(capsys):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/2061045").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    await wallet_client.validate_wallet("2061045")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        bootstrap.PROBE_UNAVAILABLE_MESSAGE.format(wallet_id="2061045") in captured.err
    )


def test_import_server_has_no_side_effects_without_env(tmp_path):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    legacy = cwd / "memory.json"
    legacy.write_text(json.dumps({"version": 1}), encoding="utf-8")

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("WALLET_ID", "WALLET_MEMORY_PATH")
    }
    env["HOME"] = str(home)
    env["PYTHONPATH"] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src")
    )

    result = subprocess.run(
        [sys.executable, "-c", "import investidor10_wallet.server"],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert legacy.exists()
    assert not (home / ".investidor10").exists()


def test_main_runs_deterministic_pipeline_and_serves(tmp_path, monkeypatch):
    events: list[str] = []
    mem_file = tmp_path / "memory.json"
    monkeypatch.setattr(wallet_client, "WALLET_ID", wallet_client.WALLET_ID)
    monkeypatch.setattr(
        wallet_client.wallet_client, "wallet_id", wallet_client.wallet_client.wallet_id
    )
    monkeypatch.setattr(
        wallet_client.rest_client, "wallet_id", wallet_client.rest_client.wallet_id
    )
    monkeypatch.setattr(server, "memory", server.memory)

    def fake_load_config(environ=None):
        events.append("config")
        return {
            "wallet_id": "12345",
            "ttl_seconds": 300.0,
            "max_stale_seconds": 7200.0,
        }

    def fake_resolve_memory_path(*args, **kwargs):
        events.append("memory_path")
        return str(mem_file)

    async def fake_validate_wallet(wallet_id: str, **_kwargs):
        events.append(f"probe:{wallet_id}")

    def fake_mcp_run(*_args, **_kwargs):
        events.append("serve")

    monkeypatch.setattr(bootstrap, "load_config", fake_load_config)
    monkeypatch.setattr(bootstrap, "resolve_memory_path", fake_resolve_memory_path)
    monkeypatch.setattr(wallet_client, "validate_wallet", fake_validate_wallet)
    monkeypatch.setattr(server.mcp, "run", fake_mcp_run)

    server.main()

    assert events == ["config", "memory_path", "probe:12345", "serve"]
    assert server.memory is not None
    assert server.memory.path == str(mem_file)
