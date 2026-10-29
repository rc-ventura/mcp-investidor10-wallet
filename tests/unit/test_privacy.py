import copy
import json
from pathlib import Path

import pytest

from investidor10_wallet import privacy

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "privacy"
SENTINEL = "9988.77"
CLASSES = ("Ticker", "Fii", "EtfInternational", "Treasure", "Crypto")


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _envelope(data):
    return {"cached": False, "fetched_at": "2026-10-28T10:00:00-03:00", "data": data}


@pytest.fixture
def on():
    privacy.configure({"mask_values": True})
    yield
    privacy.configure({"mask_values": False})


def test_disabled_mode_returns_the_envelope_untouched():
    privacy.configure({"mask_values": False})
    envelope = _envelope(_load("summary.json"))
    assert privacy.mask("summary", envelope) is envelope
    assert "privacy" not in envelope


def test_configure_tolerates_a_config_without_the_key():
    privacy.configure({})
    assert privacy.enabled() is False


def test_summary_keeps_only_percentages_and_currency(on):
    masked = privacy.mask("summary", _envelope(_load("summary.json")))
    assert set(masked["data"]) == {
        "type",
        "variation",
        "profit_twr",
        "profit_twr_12m",
        "currency",
    }
    assert masked["privacy"] == {
        "masked": True,
        "omitted": ["applied", "equity", "profit_amount", "profit_twr_12m_amount"],
    }
    assert masked["cached"] is False
    assert masked["fetched_at"] == "2026-10-28T10:00:00-03:00"


def test_allocation_keeps_name_type_percent_per_item(on):
    masked = privacy.mask("allocation", _envelope(_load("allocation.json")))
    assert [set(item) for item in masked["data"]] == [{"name", "type", "percent"}] * 2
    assert masked["privacy"]["omitted"] == ["value"]


@pytest.mark.parametrize("asset_class", CLASSES)
def test_positions_never_leak_amounts_or_quantities(on, asset_class):
    masked = privacy.mask(
        "positions", _envelope(_load(f"positions_{asset_class}.json"))
    )
    text = json.dumps(masked)
    assert SENTINEL not in text
    row = masked["data"]["data"][0]
    for forbidden in (
        "quantity",
        "equity_brl",
        "equity_total",
        "earnings_received",
        "target_price_amount",
        "gnr",
        "gnp",
        "ranking",
    ):
        assert forbidden not in row
    assert set(masked["data"]) == {"total", "draw", "data"}
    assert row["percent_wallet"] == 15.2
    assert row["percent_ideal"] == 8.0
    assert "weighted" in masked["privacy"]["omitted"]
    assert "quantity" in masked["privacy"]["omitted"]


def test_positions_keep_indicators_ratings_and_unit_prices(on):
    row = privacy.mask("positions", _envelope(_load("positions_Ticker.json")))["data"][
        "data"
    ][0]
    for kept in ("ticker", "dy", "p_vp", "rating", "avg_price", "current_price", "yoc"):
        assert kept in row


def test_unknown_field_is_omitted_and_reported(on):
    payload = _load("summary.json")
    payload["brand_new_field"] = 123
    masked = privacy.mask("summary", _envelope(payload))
    assert "brand_new_field" not in masked["data"]
    assert "brand_new_field" in masked["privacy"]["omitted"]


def test_unknown_field_inside_a_position_row_is_omitted(on):
    payload = _load("positions_Fii.json")
    payload["data"][0]["total_cost_brl"] = 100.0
    masked = privacy.mask("positions", _envelope(payload))
    assert "total_cost_brl" not in masked["data"]["data"][0]
    assert "total_cost_brl" in masked["privacy"]["omitted"]


@pytest.mark.parametrize("nested", [{"amount": 123456.78}, [123456.78]])
def test_allowed_field_holding_a_nested_value_is_omitted(on, nested):
    payload = _load("positions_Ticker.json")
    payload["data"][0]["current_price"] = nested
    masked = privacy.mask("positions", _envelope(payload))
    assert "current_price" not in masked["data"]["data"][0]
    assert "current_price" in masked["privacy"]["omitted"]
    assert "123456.78" not in json.dumps(masked)


def test_positions_truncated_flag_survives_masking(on):
    payload = _load("positions_Fii.json")
    payload["truncated"] = True
    masked = privacy.mask("positions", _envelope(payload))
    assert masked["data"]["truncated"] is True


def test_omitted_is_sorted_and_deduplicated_across_rows(on):
    payload = _load("positions_Ticker.json")
    payload["data"] = [copy.deepcopy(payload["data"][0]) for _ in range(3)]
    omitted = privacy.mask("positions", _envelope(payload))["privacy"]["omitted"]
    assert omitted == sorted(set(omitted))


def test_masking_does_not_mutate_the_cached_source_payload(on):
    payload = _load("positions_Ticker.json")
    snapshot = copy.deepcopy(payload)
    privacy.mask("positions", _envelope(payload))
    assert payload == snapshot


def test_non_dict_allocation_items_never_pass_through(on):
    masked = privacy.mask("allocation", _envelope(["raw string", 42]))
    assert masked["data"] == []


def test_unavailable_error_names_the_tool_and_the_alternatives():
    payload = privacy.unavailable_error("get_earnings")
    assert payload["error"]["code"] == "privacy_mode_unavailable"
    message = payload["error"]["message"]
    assert "get_earnings is unavailable" in message
    assert "get_wallet_allocation" in message and "get_wallet_positions" in message
    assert "do not estimate" in message
