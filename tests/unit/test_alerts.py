"""Unit tests for the price-alert state machine in the memory store (T034/US6).

Alerts are evaluated only at session open (get_session_context); there is no
continuous monitoring. Contract: direction=below triggers when
price <= limit_price, direction=above when price >= limit_price (inclusive);
triggered and cancelled are terminal states (SC-006: no duplicate triggers).
"""

import pytest

from memory_store import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "memory.json"))


def test_create_price_alert_defaults_to_active(store):
    alert = store.create_price_alert("PETR4", "below", 30.0)
    assert alert["ticker"] == "PETR4"
    assert alert["direction"] == "below"
    assert alert["limit_price"] == 30.0
    assert alert["state"] == "active"
    assert alert["triggered_at"] is None
    assert alert["triggered_price"] is None


def test_create_price_alert_validates_params(store):
    with pytest.raises(ValueError):
        store.create_price_alert("  ", "below", 30.0)
    with pytest.raises(ValueError):
        store.create_price_alert("PETR4", "sideways", 30.0)
    with pytest.raises(ValueError):
        store.create_price_alert("PETR4", "below", 0)
    with pytest.raises(ValueError):
        store.create_price_alert("PETR4", "below", -5)
    with pytest.raises(ValueError):
        store.create_price_alert("PETR4", "below", "thirty")


def test_list_price_alerts_filters_by_state(store):
    active = store.create_price_alert("PETR4", "below", 30.0)
    store.create_price_alert("VALE3", "above", 100.0)
    store.cancel_price_alert(active["id"])
    assert [a["id"] for a in store.list_price_alerts("active")] != [active["id"]]
    assert len(store.list_price_alerts("cancelled")) == 1
    assert len(store.list_price_alerts()) == 2
    with pytest.raises(ValueError):
        store.list_price_alerts("exploded")


def test_cancel_is_terminal_and_validates(store):
    alert = store.create_price_alert("PETR4", "below", 30.0)
    cancelled = store.cancel_price_alert(alert["id"])
    assert cancelled["state"] == "cancelled"
    with pytest.raises(ValueError):
        store.cancel_price_alert(alert["id"])  # already cancelled
    assert store.cancel_price_alert(999) is None  # not found


def test_below_triggers_when_price_equal_or_below_limit(store):
    alert = store.create_price_alert("PETR4", "below", 30.0)
    # Boundary is inclusive (price == limit triggers).
    triggered = store.evaluate_alerts({"PETR4": 30.0})
    assert len(triggered) == 1
    assert triggered[0]["id"] == alert["id"]
    assert triggered[0]["state"] == "triggered"
    assert triggered[0]["triggered_price"] == 30.0
    assert triggered[0]["triggered_at"]


def test_above_triggers_when_price_equal_or_above_limit(store):
    alert = store.create_price_alert("VALE3", "above", 65.0)
    triggered = store.evaluate_alerts({"VALE3": 65.0})
    assert len(triggered) == 1
    assert triggered[0]["id"] == alert["id"]


def test_no_trigger_when_price_not_met_or_quote_missing(store):
    store.create_price_alert("PETR4", "below", 30.0)
    assert store.evaluate_alerts({"PETR4": 31.0}) == []
    # A missing quote (check failed) must not trigger nor fail the evaluation.
    assert store.evaluate_alerts({}) == []


def test_triggered_alert_never_fires_again(store):
    alert = store.create_price_alert("PETR4", "below", 30.0)
    store.evaluate_alerts({"PETR4": 29.0})
    assert store.evaluate_alerts({"PETR4": 29.0}) == []
    assert len([a for a in store.list_price_alerts() if a["state"] == "triggered"]) == 1
    assert alert["id"] not in [a["id"] for a in store.list_price_alerts("active")]


def test_multiple_alerts_same_ticker_evaluate_independently(store):
    store.create_price_alert("PETR4", "below", 30.0)
    store.create_price_alert("PETR4", "below", 25.0)
    triggered = store.evaluate_alerts({"PETR4": 28.0})
    assert len(triggered) == 1
    assert triggered[0]["limit_price"] == 30.0