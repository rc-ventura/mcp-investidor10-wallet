import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
README = (REPO / "README.md").read_text(encoding="utf-8")
MARKETPLACE = "rc-ventura/mcp-investidor10-wallet"


def _section(title_pattern: str) -> str:
    match = re.search(rf"^## [^\n]*{title_pattern}[^\n]*$", README, re.MULTILINE)
    assert match, f"seção '{title_pattern}' não encontrada no README"
    rest = README[match.end() :]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


@pytest.fixture(scope="module")
def desktop() -> str:
    return _section("Claude Desktop")


def test_desktop_section_has_the_marketplace_address_in_a_code_block(desktop):
    blocks = re.findall(r"```[^\n]*\n(.*?)```", desktop, re.DOTALL)
    assert any(MARKETPLACE in block for block in blocks)


@pytest.mark.parametrize(
    "step",
    [
        r"adicion\w+ o marketplace",
        r"instal\w+ o plugin",
        r"configure na página",
        r"atualizar",
        r"desinstalar",
    ],
)
def test_desktop_section_covers_every_step(desktop, step):
    assert re.search(step, desktop.lower())


def test_desktop_section_states_the_requirements_and_limits(desktop):
    text = desktop.lower()
    assert "plano pago" in text
    assert "chat" in text and "cowork" in text
    assert "linux" in text
    assert "INSTALACAO-DESKTOP" in desktop
    assert "uv" in desktop


def test_desktop_section_tells_how_to_remove_the_old_manual_entry(desktop):
    assert "claude_desktop_config.json" in desktop


def test_desktop_section_never_asks_the_link_in_the_conversation(desktop):
    text = desktop.lower()
    assert "na página" in text
    assert "nunca" in text


def test_readme_links_the_privacy_doc():
    assert "docs/PRIVACY.md" in README


def test_readme_documents_the_local_configuration_and_the_doctor():
    assert "configure" in README
    assert "--link" in README
    assert "doctor" in README
    assert "~/.investidor10/config.json" in README


def test_readme_counts_the_twenty_tools_and_names_the_setup_tool():
    assert "Tools (20)" in README
    assert "open_wallet_setup" in README
    assert "19 tools" not in README
    assert "Tools (19)" not in README


def test_readme_does_not_ask_for_a_wallet_id_variable_anymore():
    assert "o servidor aborta sem ela" not in README
    assert "WALLET_ID` | Sim" not in README
    assert '"env": { "WALLET_ID"' not in README


def test_readme_uses_the_real_public_wallet_link():
    assert "/wallet/public/" in README
    assert "?h=" in README
