import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "PRIVACY.md"
README = REPO / "README.md"
URL = "https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/PRIVACY.md"

SECTIONS = (
    "## O que vai para onde",
    "## A credencial é o link",
    "## Modo privacidade",
    "## Privacidade total",
    "## Memória em pasta sincronizada",
    "## Telemetria",
)


def test_privacy_doc_has_the_six_required_sections_in_order():
    text = DOC.read_text(encoding="utf-8")
    positions = [text.index(section) for section in SECTIONS]
    assert positions == sorted(positions)


def test_privacy_doc_answers_the_four_questions():
    text = DOC.read_text(encoding="utf-8")
    for needle in (
        "Investidor10",
        "provedor do modelo",
        "memory.json",
        "memory.json.log",
        "memory.json.lock",
        "WALLET_MASK_VALUES",
        "botão de mascarar",
        "só visual",
        "senha",
    ):
        assert needle in text, needle


def test_privacy_doc_states_the_limits_of_the_mode():
    text = DOC.read_text(encoding="utf-8")
    assert "não é anonimização" in text
    assert "texto livre" in text
    assert "não envia telemetria" in text
    assert "Dropbox" in text


def test_privacy_doc_has_no_emojis():
    text = DOC.read_text(encoding="utf-8")
    assert not re.search("[\U0001f000-\U0001faff☀-➿]", text)


def test_readme_links_the_privacy_doc_near_the_top():
    text = README.read_text(encoding="utf-8")
    assert URL in text
    assert text.index(URL) < text.index("## Status")


def test_readme_documents_mask_variable_and_sync_folder_limit():
    text = README.read_text(encoding="utf-8")
    assert "`WALLET_MASK_VALUES`" in text
    assert "Dropbox" in text
    assert "duas máquinas" in text


def test_readme_no_longer_describes_the_legacy_migration():
    text = README.read_text(encoding="utf-8")
    assert "migrada" not in text
    assert "migrar a memória" not in text
