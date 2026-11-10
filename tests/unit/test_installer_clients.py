import sys

import pytest

from investidor10_wallet import __version__
from investidor10_wallet.installer import ClientRegistration, clients

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX-only: fake clients are /bin/sh scripts"
)


def _registration():
    return ClientRegistration(command="uvx", args=["mcp-investidor10-wallet"])


def test_detect_false_when_binary_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert clients.ClaudeAdapter().detect() is False


def test_claude_registers_with_scope_user(fake_bin_dir):
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert "claude mcp add carteira --scope user -- uvx mcp-investidor10-wallet" in log


def test_devin_registers_with_user_scope(fake_bin_dir):
    outcome = clients.DevinAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert "devin mcp add -s user carteira -- uvx mcp-investidor10-wallet" in log


def test_codex_registers_with_the_separator(fake_bin_dir):
    outcome = clients.CodexAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert "codex mcp add carteira -- uvx mcp-investidor10-wallet" in log


def test_gemini_registers_with_user_scope(fake_bin_dir):
    outcome = clients.GeminiAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert "gemini mcp add -s user carteira uvx mcp-investidor10-wallet" in log


def test_collision_skip_keeps_existing(fake_bin_dir, monkeypatch):
    (fake_bin_dir / "mcp-list.out").write_text("carteira\n")
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "skipped_present"
    assert "mcp add" not in (fake_bin_dir / "calls.log").read_text()


def test_collision_update_reruns_add(fake_bin_dir, monkeypatch):
    (fake_bin_dir / "mcp-list.out").write_text("carteira\n")
    monkeypatch.setattr("builtins.input", lambda prompt: "s")
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "updated"
    assert "mcp add" in (fake_bin_dir / "calls.log").read_text()


def test_plugin_install_commands_use_canonical_sources(fake_bin_dir):
    assert clients.ClaudeAdapter().plugin_install_commands() == [
        [
            "claude",
            "plugin",
            "marketplace",
            "add",
            f"rc-ventura/mcp-investidor10-wallet#v{__version__}",
        ],
        ["claude", "plugin", "install", "investidor10-carteira@investidor10"],
    ]
    assert clients.DevinAdapter().plugin_install_commands() == [
        [
            "devin",
            "plugins",
            "install",
            "rc-ventura/mcp-investidor10-wallet#plugin",
            "-y",
        ]
    ]
    assert clients.CodexAdapter().plugin_install_commands() == [
        ["codex", "plugin", "marketplace", "add", "rc-ventura/mcp-investidor10-wallet"],
        ["codex", "plugin", "add", "investidor10-carteira@investidor10"],
    ]
    assert clients.GeminiAdapter().plugin_install_commands() == [
        [
            "gemini",
            "extensions",
            "install",
            "https://github.com/rc-ventura/mcp-investidor10-wallet",
        ]
    ]


def test_failed_registration_reports_pt_br(fake_bin_dir):
    (fake_bin_dir / "exit-code").write_text("1")
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "failed"
    assert "falha" in outcome.message


def test_codex_plugin_commands_empty_without_binary(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert clients.CodexAdapter().plugin_install_commands() == []


@pytest.mark.parametrize(
    "adapter",
    [
        clients.ClaudeAdapter(),
        clients.DevinAdapter(),
        clients.CodexAdapter(),
        clients.GeminiAdapter(),
    ],
    ids=lambda adapter: adapter.client_id,
)
def test_add_command_carries_no_wallet_variable(adapter):
    command = adapter.add_command(_registration())
    joined = " ".join(command)
    assert "WALLET_ID" not in joined
    assert "WALLET_HASH" not in joined
    assert "-e" not in command
    assert "--env" not in command
    assert "env" not in command


PLUGIN_ID = "investidor10-carteira@investidor10"
SYNCED_ID = "investidor10-carteira@synced"


def _log(fake_bin_dir):
    return (fake_bin_dir / "calls.log").read_text()


def _claude_calls(fake_bin_dir):
    return [
        line.removeprefix("claude ")
        for line in _log(fake_bin_dir).splitlines()
        if line.startswith("claude ")
    ]


def test_claude_clean_machine_installs_plugin_without_registering_server(
    fake_bin_dir,
):
    outcome, plugin_outcomes = clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert (
        f"plugin marketplace add rc-ventura/mcp-investidor10-wallet#v{__version__}"
        in calls
    )
    assert f"plugin install {PLUGIN_ID}" in calls
    assert not any(call.startswith("mcp add") for call in calls)
    assert outcome.status == "registered"
    assert all(o.status == "registered" for o in plugin_outcomes)


def test_claude_with_synced_plugin_does_not_install_locally(fake_bin_dir):
    (fake_bin_dir / "plugin-list.out").write_text(f"{SYNCED_ID}\n")
    outcome, _ = clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert not any("marketplace add" in call for call in calls)
    assert not any(call.startswith("plugin install") for call in calls)
    assert outcome.status == "skipped_present"
    assert "Claude Desktop" in outcome.message


def test_claude_synced_and_local_copy_offers_to_uninstall_the_local_one(
    fake_bin_dir, monkeypatch
):
    (fake_bin_dir / "plugin-list.out").write_text(f"{SYNCED_ID}\n{PLUGIN_ID}\n")
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "s")
    clients.ClaudeAdapter().install_plugin()
    assert len(asked) == 1
    assert f"plugin uninstall {PLUGIN_ID}" in _claude_calls(fake_bin_dir)


def test_claude_synced_and_local_copy_kept_when_the_user_declines(
    fake_bin_dir, monkeypatch
):
    (fake_bin_dir / "plugin-list.out").write_text(f"{SYNCED_ID}\n{PLUGIN_ID}\n")
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    outcome, _ = clients.ClaudeAdapter().install_plugin()
    assert not any("uninstall" in call for call in _claude_calls(fake_bin_dir))
    assert "duplic" in outcome.message


def test_claude_old_registration_removed_only_after_yes(fake_bin_dir, monkeypatch):
    (fake_bin_dir / "mcp-list.out").write_text(
        "carteira: uvx mcp-investidor10-wallet\n"
    )
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "s")
    outcome, _ = clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert len(asked) == 1
    assert "mcp remove carteira -s user" in calls
    assert f"plugin install {PLUGIN_ID}" in calls
    assert "duplic" not in outcome.message


def test_claude_old_registration_kept_on_refusal_installs_plugin_and_warns(
    fake_bin_dir, monkeypatch
):
    (fake_bin_dir / "mcp-list.out").write_text(
        "carteira: uvx mcp-investidor10-wallet\n"
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    outcome, _ = clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert not any("mcp remove" in call for call in calls)
    assert f"plugin install {PLUGIN_ID}" in calls
    assert "duplic" in outcome.message


def test_claude_old_registration_without_terminal_is_kept_and_warned(fake_bin_dir):
    (fake_bin_dir / "mcp-list.out").write_text(
        "carteira: uvx mcp-investidor10-wallet\n"
    )
    outcome, _ = clients.ClaudeAdapter().install_plugin()
    assert not any("mcp remove" in call for call in _claude_calls(fake_bin_dir))
    assert "duplic" in outcome.message


def test_claude_plugin_server_line_is_not_taken_for_the_old_registration(
    fake_bin_dir,
):
    (fake_bin_dir / "mcp-list.out").write_text(
        "plugin:investidor10-carteira:carteira: uvx mcp-investidor10-wallet - Connected\n"
    )
    assert clients.ClaudeAdapter().list_existing() is False


def test_claude_existing_marketplace_is_removed_and_readded_pinned_after_yes(
    fake_bin_dir, monkeypatch
):
    (fake_bin_dir / "marketplace-list.out").write_text("investidor10\n")
    (fake_bin_dir / "plugin-list.out").write_text(f"{PLUGIN_ID}\n")
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "s")
    clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert len(asked) == 1
    assert f"plugin uninstall {PLUGIN_ID}" in calls
    removed = calls.index("plugin marketplace remove investidor10")
    added = calls.index(
        f"plugin marketplace add rc-ventura/mcp-investidor10-wallet#v{__version__}"
    )
    installed = calls.index(f"plugin install {PLUGIN_ID}")
    assert removed < added < installed


def test_claude_one_question_covers_old_registration_and_old_marketplace(
    fake_bin_dir, monkeypatch
):
    (fake_bin_dir / "mcp-list.out").write_text(
        "carteira: uvx mcp-investidor10-wallet\n"
    )
    (fake_bin_dir / "marketplace-list.out").write_text("investidor10\n")
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "s")
    clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert len(asked) == 1
    assert "mcp remove carteira -s user" in calls
    assert "plugin marketplace remove investidor10" in calls


def test_claude_existing_marketplace_kept_on_refusal(fake_bin_dir, monkeypatch):
    (fake_bin_dir / "marketplace-list.out").write_text("investidor10\n")
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    clients.ClaudeAdapter().install_plugin()
    calls = _claude_calls(fake_bin_dir)
    assert not any("marketplace remove" in call for call in calls)
    assert f"plugin install {PLUGIN_ID}" in calls


def test_claude_mcp_only_registers_the_server_and_does_not_install_the_plugin(
    fake_bin_dir,
):
    outcome = clients.ClaudeAdapter().register(_registration())
    calls = _claude_calls(fake_bin_dir)
    assert outcome.status == "registered"
    assert any(call.startswith("mcp add carteira") for call in calls)
    assert not any(call.startswith("plugin install") for call in calls)
    assert "duplic" not in outcome.message


def test_claude_mcp_only_warns_when_the_plugin_is_already_there(fake_bin_dir):
    (fake_bin_dir / "plugin-list.out").write_text(f"{PLUGIN_ID}\n")
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "registered"
    assert "duplic" in outcome.message


def test_claude_failed_plugin_install_is_reported(fake_bin_dir):
    (fake_bin_dir / "fail-plugin").write_text("")
    outcome, _ = clients.ClaudeAdapter().install_plugin()
    assert outcome.status == "failed"
    assert "falha ao instalar o plugin" in outcome.message
