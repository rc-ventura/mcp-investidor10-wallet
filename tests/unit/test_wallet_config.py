import json
import os
import stat
import sys

import pytest

from investidor10_wallet import local_files, wallet_config
from investidor10_wallet.wallet_config import LinkError

WALLET = "1234567"
HASH = "abcDEF_123-xyz"
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")


@pytest.mark.parametrize(
    "text",
    [
        f"https://investidor10.com.br/wallet/public/{WALLET}?h={HASH}",
        f"https://www.investidor10.com.br/wallet/public/{WALLET}?h={HASH}",
        f'  "https://investidor10.com.br/wallet/public/{WALLET}?h={HASH}"  ',
        f"<https://investidor10.com.br/wallet/public/{WALLET}?h={HASH}>.",
        f"HTTPS://WWW.Investidor10.com.br/wallet/public/{WALLET}?h={HASH}",
        f"Minha carteira: https://investidor10.com.br/wallet/public/{WALLET}?h={HASH}, obrigado",
        f"https://investidor10.com.br/wallet/public/{WALLET}?utm_source=x&h={HASH}&utm_medium=y",
        f"https://investidor10.com.br/wallet/public/{WALLET}/?h={HASH}",
    ],
)
def test_restricted_link_variants(text):
    link = wallet_config.parse_link(text)
    assert link.mode == "restricted"
    assert link.wallet_id == WALLET
    assert link.share_hash == HASH


@pytest.mark.parametrize(
    "text",
    [
        f"https://investidor10.com.br/wallet/public/{WALLET}",
        f"https://www.investidor10.com.br/wallet/public/{WALLET}/",
        f"https://investidor10.com.br/wallet/public/{WALLET}?utm_source=x",
        f"https://investidor10.com.br/carteira/{WALLET}",
        f"https://www.investidor10.com.br/carteira/{WALLET}/",
        f"https://investidor10.com.br/carteira/{WALLET}/proventos?utm_source=x",
        f"'https://investidor10.com.br/carteira/{WALLET}'",
        f"Veja https://investidor10.com.br/carteira/{WALLET} agora",
        WALLET,
        f"  {WALLET}  ",
        f'"{WALLET}"',
    ],
)
def test_public_link_variants(text):
    link = wallet_config.parse_link(text)
    assert link.mode == "public"
    assert link.wallet_id == WALLET
    assert link.share_hash is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("não sei", "not_recognized"),
        (f"https://outro.com/carteira/{WALLET}", "wrong_host"),
        (f"https://investidor10.com.br.evil.com/carteira/{WALLET}", "wrong_host"),
        (f"https://evil.com@investidor10.com.br/carteira/{WALLET}", "wrong_host"),
        (f"https://investidor10.com.br@evil.com/carteira/{WALLET}", "wrong_host"),
        (f"http://investidor10.com.br/carteira/{WALLET}", "not_recognized"),
        (f"https://investidor10.com.br:8443/carteira/{WALLET}", "wrong_host"),
        ("123 456", "not_recognized"),
        (
            f"https://investidor10.com.br/wallet/public/{WALLET}/999?h={HASH}",
            "not_recognized",
        ),
        (
            (
                f"https://investidor10.com.br/carteira/{WALLET} "
                "https://investidor10.com.br/carteira/999"
            ),
            "multiple_links",
        ),
        (
            (
                f"https://investidor10.com.br/carteira/{WALLET} "
                f"https://investidor10.com.br/wallet/public/{WALLET}?h={HASH}"
            ),
            "multiple_links",
        ),
        ("https://investidor10.com.br/carteira/abc", "invalid_id"),
        (f"https://investidor10.com.br/wallet/public/abc?h={HASH}", "invalid_id"),
        ("12a", "not_recognized"),
        (
            f"https://investidor10.com.br/wallet/public/{WALLET}?h=",
            "missing_credential",
        ),
        (
            f"https://investidor10.com.br/wallet/public/{WALLET}?h=a%20b",
            "invalid_credential",
        ),
        (
            f"https://investidor10.com.br/wallet/public/{WALLET}?h=a/b",
            "invalid_credential",
        ),
        (
            f"https://investidor10.com.br/wallet/public/{WALLET}?h={'a' * 257}",
            "invalid_credential",
        ),
        (
            f"https://investidor10.com.br/wallet/public/{WALLET}?h=a&h=b",
            "invalid_credential",
        ),
        (f"https://investidor10.com.br/outra/{WALLET}", "not_recognized"),
        ("x" * 5000, "not_recognized"),
    ],
)
def test_link_refusals_carry_reason_and_guidance(text, reason):
    with pytest.raises(LinkError) as exc:
        wallet_config.parse_link(text)
    assert exc.value.reason == reason
    assert str(exc.value)
    assert HASH not in str(exc.value)
    assert WALLET not in str(exc.value)


def test_credential_at_the_length_limit_is_accepted():
    link = wallet_config.parse_link(
        f"https://investidor10.com.br/wallet/public/{WALLET}?h={'a' * 256}"
    )
    assert link.share_hash == "a" * 256


def valid_payload(**overrides):
    payload = {
        "version": 1,
        "wallet_id": WALLET,
        "share_hash": None,
        "mode": "public",
        "mask_values": False,
        "validated_at": "2026-11-01T10:00:00-03:00",
        "source": "setup_page",
    }
    payload.update(overrides)
    return payload


def restricted_payload(**overrides):
    return valid_payload(mode="restricted", share_hash=HASH, **overrides)


def make_config(payload=None, **overrides):
    return wallet_config.LocalConfig.from_dict(payload or valid_payload(**overrides))


def config_file(home):
    return home / ".investidor10" / "config.json"


def put_raw(home, content: bytes):
    directory = home / ".investidor10"
    directory.mkdir(mode=0o700, exist_ok=True)
    config_file(home).write_bytes(content)


def test_write_then_read_round_trip(tmp_path):
    wallet_config.write_config(tmp_path, make_config(restricted_payload()))
    loaded = wallet_config.read_config(config_file(tmp_path))
    assert loaded.wallet_id == WALLET
    assert loaded.share_hash == HASH
    assert loaded.mode == "restricted"
    assert loaded.mask_values is False
    assert loaded.source == "setup_page"


def test_written_file_contains_only_the_documented_fields(tmp_path):
    wallet_config.write_config(tmp_path, make_config(restricted_payload()))
    data = json.loads(config_file(tmp_path).read_text(encoding="utf-8"))
    assert set(data) == {
        "version",
        "wallet_id",
        "share_hash",
        "mode",
        "mask_values",
        "validated_at",
        "source",
    }
    assert data["version"] == 1


@POSIX_ONLY
def test_write_creates_private_directory_and_file(tmp_path):
    wallet_config.write_config(tmp_path, make_config())
    assert stat.S_IMODE((tmp_path / ".investidor10").stat().st_mode) == 0o700
    assert stat.S_IMODE(config_file(tmp_path).stat().st_mode) == 0o600


@POSIX_ONLY
def test_write_tightens_an_existing_loose_directory(tmp_path):
    directory = tmp_path / ".investidor10"
    directory.mkdir()
    os.chmod(directory, 0o755)
    wallet_config.write_config(tmp_path, make_config())
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700


def test_write_leaves_no_temporary_file(tmp_path):
    wallet_config.write_config(tmp_path, make_config())
    assert [p.name for p in (tmp_path / ".investidor10").iterdir()] == ["config.json"]


def test_failed_replace_keeps_old_file_and_leaves_no_temporary(tmp_path, monkeypatch):
    wallet_config.write_config(tmp_path, make_config())
    before = config_file(tmp_path).read_bytes()

    def boom(source, destination):
        raise OSError("disco cheio")

    monkeypatch.setattr(local_files.os, "replace", boom)
    with pytest.raises(OSError):
        wallet_config.write_config(tmp_path, make_config(restricted_payload()))

    assert config_file(tmp_path).read_bytes() == before
    assert [p.name for p in (tmp_path / ".investidor10").iterdir()] == ["config.json"]


def test_write_refuses_inconsistent_config(tmp_path):
    bad = wallet_config.LocalConfig(
        wallet_id=WALLET,
        share_hash=None,
        mode="restricted",
        mask_values=False,
        validated_at="2026-11-01T10:00:00-03:00",
        source="installer",
    )
    with pytest.raises(ValueError):
        wallet_config.write_config(tmp_path, bad)
    assert not config_file(tmp_path).exists()


@POSIX_ONLY
def test_write_refuses_symlinked_file_and_leaves_target_alone(tmp_path):
    directory = tmp_path / ".investidor10"
    directory.mkdir(mode=0o700)
    target = tmp_path / "elsewhere.json"
    target.write_text("{}", encoding="utf-8")
    config_file(tmp_path).symlink_to(target)

    with pytest.raises(OSError):
        wallet_config.write_config(tmp_path, make_config())

    assert target.read_text(encoding="utf-8") == "{}"
    assert config_file(tmp_path).is_symlink()


@POSIX_ONLY
def test_write_refuses_symlinked_directory(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (tmp_path / ".investidor10").symlink_to(other)
    with pytest.raises(OSError):
        wallet_config.write_config(tmp_path, make_config())
    assert list(other.iterdir()) == []


@POSIX_ONLY
def test_read_through_symlink_is_unreadable_and_link_is_untouched(tmp_path):
    directory = tmp_path / ".investidor10"
    directory.mkdir(mode=0o700)
    target = tmp_path / "elsewhere.json"
    target.write_text(json.dumps(valid_payload()), encoding="utf-8")
    config_file(tmp_path).symlink_to(target)

    state = wallet_config.resolve_state({}, tmp_path)

    assert state.status == "pending"
    assert state.reason == "unreadable"
    assert config_file(tmp_path).is_symlink()
    assert json.loads(target.read_text(encoding="utf-8")) == valid_payload()


def test_corrupt_json_is_unreadable_and_never_rewritten(tmp_path):
    put_raw(tmp_path, b"{not json")
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")
    assert config_file(tmp_path).read_bytes() == b"{not json"
    assert [p.name for p in (tmp_path / ".investidor10").iterdir()] == ["config.json"]


def test_deeply_nested_json_is_unreadable_not_a_crash(tmp_path):
    put_raw(tmp_path, b"[" * 60000)
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


def test_oversized_file_is_unreadable(tmp_path):
    put_raw(tmp_path, b" " * 200000 + json.dumps(valid_payload()).encode())
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


def test_non_utf8_bytes_are_unreadable(tmp_path):
    put_raw(tmp_path, b"\xff\xfe\x00")
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


def test_bom_from_hand_edit_is_accepted(tmp_path):
    put_raw(tmp_path, b"\xef\xbb\xbf" + json.dumps(valid_payload()).encode())
    state = wallet_config.resolve_state({}, tmp_path)
    assert state.status == "configured"


def test_non_object_json_is_unreadable(tmp_path):
    put_raw(tmp_path, b"[1, 2]")
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


@pytest.mark.parametrize("version", [2, 3, 99])
def test_future_version_is_pending_and_file_is_untouched(tmp_path, version):
    raw = json.dumps(valid_payload(version=version, extra_future_field=1)).encode()
    put_raw(tmp_path, raw)
    before = config_file(tmp_path).stat()
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "future_version")
    after = config_file(tmp_path).stat()
    assert config_file(tmp_path).read_bytes() == raw
    assert after.st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize(
    "overrides",
    [
        {"version": 0},
        {"version": "1"},
        {"version": True},
        {"version": 1.0},
        {"wallet_id": ""},
        {"wallet_id": "12a"},
        {"wallet_id": 1234567},
        {"wallet_id": "١٢٣"},
        {"share_hash": "abc"},
        {"mode": "other"},
        {"mode": "restricted"},
        {"mode": "restricted", "share_hash": ""},
        {"mode": "restricted", "share_hash": "a b"},
        {"mode": "restricted", "share_hash": "a" * 257},
        {"mode": "restricted", "share_hash": 12},
        {"mask_values": "yes"},
        {"mask_values": 1},
        {"validated_at": "ontem"},
        {"validated_at": 123},
        {"source": "manual"},
        {"source": None},
    ],
)
def test_fields_outside_the_rules_make_the_file_unreadable(tmp_path, overrides):
    put_raw(tmp_path, json.dumps(valid_payload(**overrides)).encode())
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


@pytest.mark.parametrize(
    "missing",
    [
        "version",
        "wallet_id",
        "share_hash",
        "mode",
        "mask_values",
        "validated_at",
        "source",
    ],
)
def test_missing_fields_make_the_file_unreadable(tmp_path, missing):
    payload = valid_payload()
    del payload[missing]
    put_raw(tmp_path, json.dumps(payload).encode())
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


@pytest.mark.parametrize("source", ["setup_page", "installer", "configure"])
def test_every_documented_source_is_accepted(tmp_path, source):
    put_raw(tmp_path, json.dumps(valid_payload(source=source)).encode())
    assert wallet_config.resolve_state({}, tmp_path).status == "configured"


def test_no_file_and_no_environment_is_pending_missing(tmp_path):
    state = wallet_config.resolve_state({}, tmp_path)
    assert (state.status, state.reason) == ("pending", "missing")
    assert not (tmp_path / ".investidor10").exists()


@pytest.mark.parametrize("value", ["", "  ", "abc", "12a"])
def test_unusable_environment_wallet_counts_as_missing(tmp_path, value):
    state = wallet_config.resolve_state({"WALLET_ID": value}, tmp_path)
    assert (state.status, state.reason) == ("pending", "missing")


def test_environment_wallet_without_file_is_configured_public(tmp_path):
    state = wallet_config.resolve_state({"WALLET_ID": f" {WALLET} "}, tmp_path)
    assert state.status == "configured"
    assert state.origin == "environment"
    assert state.mode == "public"
    assert state.wallet_id == WALLET
    assert state.share_hash is None
    assert state.mask_values is False


def test_valid_file_wins_over_the_environment(tmp_path):
    put_raw(tmp_path, json.dumps(restricted_payload()).encode())
    state = wallet_config.resolve_state({"WALLET_ID": "999"}, tmp_path)
    assert state.origin == "file"
    assert state.wallet_id == WALLET
    assert state.mode == "restricted"
    assert state.share_hash == HASH


def test_unreadable_file_does_not_fall_back_to_the_environment(tmp_path):
    put_raw(tmp_path, b"{not json")
    state = wallet_config.resolve_state({"WALLET_ID": "999"}, tmp_path)
    assert (state.status, state.reason) == ("pending", "unreadable")


@pytest.mark.parametrize(
    ("file_mask", "env", "expected"),
    [
        (False, None, False),
        (True, None, True),
        (False, "1", True),
        (True, "0", True),
        (False, "off", False),
        (True, "true", True),
    ],
)
def test_effective_mask_is_file_or_environment(tmp_path, file_mask, env, expected):
    put_raw(tmp_path, json.dumps(valid_payload(mask_values=file_mask)).encode())
    environ = {} if env is None else {"WALLET_MASK_VALUES": env}
    assert wallet_config.resolve_state(environ, tmp_path).mask_values is expected


def test_environment_origin_also_honors_the_mask_variable(tmp_path):
    state = wallet_config.resolve_state(
        {"WALLET_ID": WALLET, "WALLET_MASK_VALUES": "1"}, tmp_path
    )
    assert state.mask_values is True


def test_file_is_reread_only_when_its_identity_changes(tmp_path, monkeypatch):
    put_raw(tmp_path, json.dumps(valid_payload()).encode())
    reads = []
    real = wallet_config.read_config
    monkeypatch.setattr(
        wallet_config, "read_config", lambda path: reads.append(path) or real(path)
    )

    first = wallet_config.resolve_state({}, tmp_path)
    second = wallet_config.resolve_state({}, tmp_path)
    third = wallet_config.resolve_state({}, tmp_path)

    assert len(reads) == 1
    assert first == second == third


def test_replacement_by_another_process_is_seen_on_next_resolution(tmp_path):
    wallet_config.write_config(tmp_path, make_config(wallet_id="111"))
    assert wallet_config.resolve_state({}, tmp_path).wallet_id == "111"

    wallet_config.write_config(tmp_path, make_config(wallet_id="222"))

    assert wallet_config.resolve_state({}, tmp_path).wallet_id == "222"


def test_in_place_edit_with_same_size_is_seen_through_mtime(tmp_path):
    put_raw(tmp_path, json.dumps(valid_payload(wallet_id="111")).encode())
    assert wallet_config.resolve_state({}, tmp_path).wallet_id == "111"
    path = config_file(tmp_path)
    stat_before = path.stat()
    path.write_bytes(json.dumps(valid_payload(wallet_id="222")).encode())
    os.utime(path, ns=(stat_before.st_atime_ns, stat_before.st_mtime_ns + 1_000_000))

    assert wallet_config.resolve_state({}, tmp_path).wallet_id == "222"


def test_removed_file_returns_to_pending_or_environment(tmp_path):
    wallet_config.write_config(tmp_path, make_config())
    assert wallet_config.resolve_state({}, tmp_path).origin == "file"

    config_file(tmp_path).unlink()

    assert wallet_config.resolve_state({}, tmp_path).reason == "missing"
    fallback = wallet_config.resolve_state({"WALLET_ID": "999"}, tmp_path)
    assert (fallback.origin, fallback.wallet_id) == ("environment", "999")


def test_file_becoming_corrupt_after_a_good_read_is_pending(tmp_path):
    wallet_config.write_config(tmp_path, make_config())
    assert wallet_config.resolve_state({}, tmp_path).status == "configured"

    config_file(tmp_path).write_bytes(b"{")

    assert wallet_config.resolve_state({}, tmp_path).reason == "unreadable"


def test_masked_wallet_shows_ellipsis_and_last_two_digits():
    assert wallet_config.masked_wallet("1234567") == "…67"
    assert wallet_config.masked_wallet("5") == "…5"
    assert wallet_config.masked_wallet("") == "…"


def test_state_shows_a_masked_wallet_and_never_leaks_ids_or_credentials(tmp_path):
    put_raw(tmp_path, json.dumps(restricted_payload()).encode())
    state = wallet_config.resolve_state({}, tmp_path)

    assert state.wallet == "…67"
    for text in (
        repr(state),
        str(state),
        f"{state}",
        repr(make_config(restricted_payload())),
    ):
        assert HASH not in text
        assert WALLET not in text


def test_link_repr_hides_the_credential():
    link = wallet_config.parse_link(
        f"https://investidor10.com.br/wallet/public/{WALLET}?h={HASH}"
    )
    assert HASH not in repr(link)
    assert HASH not in str(link)


def test_pending_states_have_no_wallet_or_credential(tmp_path):
    state = wallet_config.resolve_state({}, tmp_path)
    assert state.wallet_id is None
    assert state.share_hash is None
    assert state.wallet is None


def test_invalid_privacy_flag_in_the_environment_fails_closed(tmp_path):
    state = wallet_config.resolve_state(
        {"WALLET_ID": WALLET, "WALLET_MASK_VALUES": "talvez"}, tmp_path
    )
    assert state.status == "configured"
    assert state.mask_values is True
