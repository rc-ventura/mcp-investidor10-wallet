"""Unit tests for the price-alert state machine in the memory store (T034/US6).

Alerts are evaluated only at session open (get_session_context); there is no
continuous monitoring. Contract: direction=below triggers when
price <= limit_price, direction=above when price >= limit_price (inclusive);
triggered and cancelled are terminal states (SC-006: no duplicate triggers).
"""

from pathlib import Path

import pytest

import memory_store
from memory_store import MemoryStore, MemoryUnavailableError


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
    with pytest.raises(ValueError):
        store.create_price_alert("ABC?raw=1#frag", "below", 30)
    for price in (float("nan"), float("inf"), -float("inf"), True):
        with pytest.raises(ValueError):
            store.create_price_alert("PETR4", "below", price)
    assert "NaN" not in Path(store.path).read_text()


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


def test_evaluate_alerts_persists_all_triggers_in_one_save(store, monkeypatch):
    store.create_price_alert("PETR4", "below", 30.0)
    store.create_price_alert("VALE3", "below", 20.0)
    calls = []
    original = store.save

    def counting_save():
        calls.append(1)
        original()

    monkeypatch.setattr(store, "save", counting_save)
    triggered = store.evaluate_alerts({"PETR4": 10.0, "VALE3": 10.0})
    assert len(triggered) == 2
    assert len(calls) == 1


def test_evaluate_alerts_failed_save_persists_nothing(tmp_path, monkeypatch):
    store = MemoryStore(str(tmp_path / "memory.json"))
    store.create_price_alert("PETR4", "below", 30.0)
    store.create_price_alert("VALE3", "below", 20.0)
    monkeypatch.setattr("memory_store.os.replace", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(MemoryUnavailableError):
        store.evaluate_alerts({"PETR4": 10.0, "VALE3": 10.0})
    # The failed save persisted nothing: every alert is still active for the
    # next session, so no satisfied notification was silently lost.
    reloaded = MemoryStore(store.path)
    assert len(reloaded.list_price_alerts("active")) == 2


def test_oversized_limit_is_skipped_without_error(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.create_price_alert("PETR4", "below", 30.0)
    store.data["alerts"][0]["limit_price"] = 10**400
    store.save()
    reloaded = MemoryStore(str(path))
    assert reloaded.evaluate_alerts({"PETR4": 10.0}) == []
    assert len(reloaded.list_price_alerts("active")) == 1


def test_persisted_regex_invalid_ticker_is_invalid_alert(tmp_path):
    """A hand-edited alert with a regex-invalid ticker must be treated as an
    invalid alert (skipped, never evaluated) — same regex as create_price_alert."""
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.create_price_alert("PETR4", "below", 30.0)
    store.data["alerts"][0]["ticker"] = "PETR4??"
    store.save()
    reloaded = MemoryStore(str(path))
    alert = reloaded.list_price_alerts()[0]
    assert memory_store.alert_is_valid(alert) is False
    assert reloaded.evaluate_alerts({"PETR4": 10.0}) == []
    assert len(reloaded.list_price_alerts("active")) == 1


def test_persisted_lowercase_ticker_still_valid(tmp_path):
    """Ticker validity is checked on the normalized ticker: a hand-edited
    lowercase ticker stays evaluable (server bootstrap normalizes it)."""
    path = tmp_path / "memory.json"
    store = MemoryStore(str(path))
    store.create_price_alert("PETR4", "below", 30.0)
    store.data["alerts"][0]["ticker"] = "petr4"
    store.save()
    reloaded = MemoryStore(str(path))
    assert memory_store.alert_is_valid(reloaded.list_price_alerts()[0]) is True