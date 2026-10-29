import json
import os
import subprocess
import sys
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


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", " on ", "oN"])
def test_mask_values_accepts_truthy_spellings(value):
    config = bootstrap.load_config({"WALLET_ID": "1", "WALLET_MASK_VALUES": value})
    assert config["mask_values"] is True


@pytest.mark.parametrize("value", ["0", "false", "False", "NO", " off "])
def test_mask_values_accepts_falsy_spellings(value):
    config = bootstrap.load_config({"WALLET_ID": "1", "WALLET_MASK_VALUES": value})
    assert config["mask_values"] is False


def test_mask_values_defaults_to_off_when_absent():
    assert bootstrap.load_config({"WALLET_ID": "1"})["mask_values"] is False


@pytest.mark.parametrize("value", ["talvez", "", "  ", "2", "sim"])
def test_mask_values_rejects_unknown_values_with_pt_br_message(value):
    with pytest.raises(SystemExit) as exc:
        bootstrap.load_config({"WALLET_ID": "1", "WALLET_MASK_VALUES": value})
    assert str(exc.value) == bootstrap.INVALID_MASK_MESSAGE.format(value=value)
    assert "1/true/yes/on" in str(exc.value)
    assert "0/false/no/off" in str(exc.value)


def test_config_failure_makes_no_network_calls():
    with respx.mock(assert_all_called=False) as router:
        router.get(url__regex=r".*").mock(
            side_effect=AssertionError("no network call expected")
        )
        with pytest.raises(SystemExit):
            bootstrap.load_config({"WALLET_ID": "nope"})


def test_override_returns_custom_path_verbatim_and_inspects_nothing(tmp_path):
    home = tmp_path / "home"
    custom = tmp_path / "custom" / "mem.json"

    resolved = bootstrap.resolve_memory_path(
        home=home, environ={"WALLET_MEMORY_PATH": str(custom)}
    )

    assert resolved == str(custom)
    assert not (home / ".investidor10").exists()
    assert not custom.parent.exists()


def test_without_override_returns_canonical_path_and_first_save_persists(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    resolved = bootstrap.resolve_memory_path(home=home, environ={})

    canonical_file = home / ".investidor10" / "memory.json"
    assert resolved == str(canonical_file)
    assert canonical_file.parent.is_dir()
    store = MemoryStore(resolved)
    assert store.available is True
    store.save_rule("comprar apenas ativos com lucro consistente")
    assert len(MemoryStore(resolved).get_rules()) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: file mode bits")
def test_canonical_dir_is_0700_and_memory_file_is_0600(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    resolved = bootstrap.resolve_memory_path(home=home, environ={})

    canonical_file = Path(resolved)
    MemoryStore(resolved).save_rule("regra")
    assert (canonical_file.parent.stat().st_mode & 0o777) == 0o700
    assert (canonical_file.stat().st_mode & 0o777) == 0o600


def test_stray_memory_file_in_cwd_is_ignored_and_untouched(
    tmp_path, monkeypatch, capsys
):
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    stray = cwd / "memory.json"
    stray.write_text('{"version": 1, "source": "stray"}', encoding="utf-8")
    before = (stray.read_bytes(), stray.stat().st_ino, stray.stat().st_mtime_ns)
    monkeypatch.chdir(cwd)

    resolved = bootstrap.resolve_memory_path(home=home, environ={})

    assert resolved == str(home / ".investidor10" / "memory.json")
    assert not Path(resolved).exists()
    assert (stray.read_bytes(), stray.stat().st_ino, stray.stat().st_mtime_ns) == before
    assert [entry.name for entry in cwd.iterdir()] == ["memory.json"]
    assert capsys.readouterr().err == ""


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlink creation")
def test_symlinked_canonical_file_aborts_with_pt_br(tmp_path):
    home = tmp_path / "home"
    canonical_dir = home / ".investidor10"
    canonical_dir.mkdir(parents=True, mode=0o700)
    target = tmp_path / "elsewhere.json"
    target.write_text('{"version": 1}', encoding="utf-8")
    (canonical_dir / "memory.json").symlink_to(target)

    with pytest.raises(SystemExit) as exc:
        bootstrap.resolve_memory_path(home=home, environ={})

    assert str(canonical_dir) in str(exc.value)
    assert target.read_text(encoding="utf-8") == '{"version": 1}'


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: symlink creation")
def test_symlinked_canonical_dir_aborts_with_pt_br_and_leaves_target_alone(tmp_path):
    home = tmp_path / "home"
    other = tmp_path / "other"
    home.mkdir()
    other.mkdir(mode=0o755)
    os.chmod(other, 0o755)
    (home / ".investidor10").symlink_to(other)

    with pytest.raises(SystemExit) as exc:
        bootstrap.resolve_memory_path(home=home, environ={})

    assert str(home / ".investidor10") in str(exc.value)
    assert (other.stat().st_mode & 0o777) == 0o755


@respx.mock
async def test_probe_200_succeeds_silently(capsys):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/1234567").mock(
        return_value=httpx.Response(200, json={"applied": 1, "equity": 1})
    )

    await wallet_client.validate_wallet("1234567")

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
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/1234567").mock(
        return_value=httpx.Response(status_code)
    )

    with pytest.raises(SystemExit) as exc:
        await wallet_client.validate_wallet("1234567")

    assert str(exc.value) == bootstrap.WALLET_PRIVATE_MESSAGE.format(
        wallet_id="1234567"
    )


@pytest.mark.parametrize("status_code", [500, 502, 503, 429])
@respx.mock
async def test_probe_5xx_and_other_status_warns_and_continues(status_code, capsys):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/1234567").mock(
        return_value=httpx.Response(status_code)
    )

    await wallet_client.validate_wallet("1234567")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        bootstrap.PROBE_UNAVAILABLE_MESSAGE.format(wallet_id="1234567") in captured.err
    )


@respx.mock
async def test_probe_timeout_warns_on_stderr_and_continues(capsys):
    respx.get(f"{wallet_client.WALLET_PROXY_BASE_URL}/summary/metrics/1234567").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    await wallet_client.validate_wallet("1234567")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        bootstrap.PROBE_UNAVAILABLE_MESSAGE.format(wallet_id="1234567") in captured.err
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
