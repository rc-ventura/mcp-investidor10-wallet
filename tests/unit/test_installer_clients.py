from investidor10_wallet.installer import ClientRegistration, clients


def _registration():
    return ClientRegistration(
        command="uvx",
        args=["mcp-investidor10-wallet"],
        env={"WALLET_ID": "1234567"},
    )


def test_detect_false_when_binary_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert clients.ClaudeAdapter().detect() is False


def test_claude_registers_with_scope_user(fake_bin_dir):
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert (
        "claude mcp add carteira --scope user -- env WALLET_ID=1234567 uvx mcp-investidor10-wallet"
        in log
    )


def test_devin_registers_with_user_scope(fake_bin_dir):
    outcome = clients.DevinAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert (
        "devin mcp add -s user carteira -e WALLET_ID=1234567 -- uvx mcp-investidor10-wallet"
        in log
    )


def test_codex_registers_with_env_flag(fake_bin_dir):
    outcome = clients.CodexAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert (
        "codex mcp add carteira --env WALLET_ID=1234567 -- uvx mcp-investidor10-wallet"
        in log
    )


def test_gemini_registers_with_user_scope(fake_bin_dir):
    outcome = clients.GeminiAdapter().register(_registration())
    assert outcome.status == "registered"
    log = (fake_bin_dir / "calls.log").read_text()
    assert (
        "gemini mcp add -s user -e WALLET_ID=1234567 carteira uvx mcp-investidor10-wallet"
        in log
    )


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


def test_failed_registration_reports_pt_br(fake_bin_dir):
    (fake_bin_dir / "exit-code").write_text("1")
    outcome = clients.ClaudeAdapter().register(_registration())
    assert outcome.status == "failed"
    assert "falha" in outcome.message
