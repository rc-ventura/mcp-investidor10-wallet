import inspect

import pytest
from fastmcp import Client

from investidor10_wallet import server
from investidor10_wallet.server import mcp

TOOLS = (
    "get_wallet_summary",
    "get_wallet_allocation",
    "get_wallet_positions",
    "get_asset_quote",
    "get_earnings",
    "get_patrimony_history",
    "create_price_alert",
    "list_price_alerts",
    "cancel_price_alert",
    "get_session_context",
    "get_wallet_goal",
    "set_wallet_goal",
    "save_thesis",
    "get_theses",
    "save_rule",
    "get_rules",
    "log_decision",
    "record_decision_outcome",
    "log_insight",
)

SERVED_RULES = {
    "get_asset_quote": ("15 minutes", "fetched_at"),
    "get_wallet_positions": ("percent_ideal", "fetched_at"),
    "get_earnings": ("data.sum", "fetched_at"),
    "get_patrimony_history": ("fetched_at",),
    "create_price_alert": ("pending check",),
}


def _text_after_args(doc):
    lines = inspect.cleandoc(doc).splitlines()
    if "Args:" not in lines:
        return ""
    index = lines.index("Args:") + 1
    while index < len(lines) and lines[index].strip() and lines[index].startswith(" "):
        index += 1
    return "\n".join(lines[index:]).strip()


@pytest.mark.parametrize("name", TOOLS)
def test_no_tool_docstring_has_text_after_the_args_block(name):
    assert _text_after_args(getattr(server, name).__doc__) == ""


async def test_every_tool_is_covered_by_this_check():
    async with Client(mcp) as client:
        served = {tool.name for tool in await client.list_tools()}
    assert served == set(TOOLS)


async def test_usage_rules_reach_the_model_in_the_served_descriptions():
    async with Client(mcp) as client:
        descriptions = {t.name: t.description for t in await client.list_tools()}
    for name, phrases in SERVED_RULES.items():
        for phrase in phrases:
            assert phrase in descriptions[name], (name, phrase)
