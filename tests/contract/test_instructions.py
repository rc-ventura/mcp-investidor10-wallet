import pytest

from investidor10_wallet.server import mcp

FORBIDDEN = ("portuguese", "persona", "you are", "always respond")


def test_instructions_state_purpose_and_index():
    text = mcp.instructions
    assert text
    assert len(text) <= 600
    for needle in ("get_session_context", "privacy.masked", "isError", "15 minutes"):
        assert needle in text


@pytest.mark.parametrize("word", FORBIDDEN)
def test_instructions_carry_no_agent_behavior(word):
    assert word not in mcp.instructions.lower()
