import json
from types import SimpleNamespace

import pandas as pd
import pytest

from restaurant_ops.actions import execute_actions, validate_action
from restaurant_ops.analytics import detect_cost_creep
from restaurant_ops.llm import ask, parse_response
from restaurant_ops.manager import RestaurantManager
from restaurant_ops.storage import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


def test_compare_prices_picks_cheapest_and_skips_unknown():
    m = RestaurantManager.sample()
    res = m.compare_prices(["Grenadine", "Wine", "Unobtainium"])
    assert res == {"Grenadine": ("VendorB", 11.5), "Wine": ("VendorC", 13.5)}


def test_weekly_order_groups_by_vendor():
    order = RestaurantManager.sample().compile_weekly_order(["Beef", "Plastic Cups"])
    assert order == {"VendorA": [("Beef", 5.25)], "VendorC": [("Plastic Cups", 8.0)]}


def test_pnl():
    m = RestaurantManager()
    m.record_sale(100); m.record_expense(30)
    assert m.generate_pnl() == (100, 30, 70)


def test_roundtrip_and_atomic_save(store):
    m = RestaurantManager.sample()
    m.orders.append({"time": "t", "platform": "POS", "item": "Burger", "qty": 2})
    m.post_job_update("hire", "Cook", ["Indeed"])
    store.save(m)
    assert not list(store.data_dir.glob("*.tmp"))
    m2 = store.load()
    assert m2.to_dict() == m.to_dict()


def test_load_without_file_returns_sample(store):
    assert [p.name for p in store.load().platforms] == ["POS", "Website", "DeliveryApp"]


def test_bad_job_action_rejected():
    with pytest.raises(ValueError):
        RestaurantManager().post_job_update("promote", "x", [])


@pytest.mark.parametrize("action,ok", [
    ({"type": "record_sale", "amount": 10}, True),
    ({"type": "record_sale", "amount": -1}, False),
    ({"type": "record_sale", "amount": "nan"}, False),
    ({"type": "record_sale", "amount": "inf"}, False),
    ({"type": "update_menu_price", "item": "Fries"}, False),
    ({"type": "update_menu_price", "item": " ", "price": 3}, False),
    ({"type": "rm_rf"}, False),
    ("nope", False),
])
def test_validate_action(action, ok):
    assert (validate_action(action) is None) == ok


def test_execute_actions_applies_valid_and_skips_invalid(store):
    m = RestaurantManager.sample()
    out = execute_actions(m, store, [
        {"type": "update_menu_price", "item": "Fries", "price": 3.99},
        {"type": "add_vendor_price", "vendor": "VendorA", "item": "Beef", "price": "5.50"},
        {"type": "set_hours", "hours": "11am–9pm"},
        {"type": "record_expense", "amount": -5},
    ])
    assert all(p.menu["Fries"] == 3.99 and p.hours == "11am–9pm" for p in m.platforms)
    assert m.vendor_prices["VendorA"]["Beef"] == 5.5
    assert m.expenses == []
    assert out[-1].startswith("Skipped")
    assert len(store.load_vendor_history()) == 1
    assert len(store.load_audit()) == 3


def test_cost_creep_latest_vs_previous():
    df = pd.DataFrame([
        {"time": "1", "vendor": "A", "item": "Beef", "price": 5.0},
        {"time": "2", "vendor": "A", "item": "Beef", "price": 5.5},
        {"time": "1", "vendor": "A", "item": "Cups", "price": 8.0},
    ])
    res = detect_cost_creep(df)
    assert len(res) == 1
    assert res.iloc[0]["delta_pct"] == pytest.approx(10.0)
    assert detect_cost_creep(pd.DataFrame(columns=["time", "vendor", "item", "price"])).empty


def test_upload_strips_path_and_queues(store):
    p = store.save_upload("../../etc/evil.csv", b"a,b", "Other")
    assert p.parent == store.upload_dir and p.name.endswith("_evil.csv")
    assert json.loads(store.upload_queue_path.read_text())["filename"] == "evil.csv"


def test_export_zip_contents(store):
    import io, zipfile
    z = zipfile.ZipFile(io.BytesIO(store.export_zip(RestaurantManager.sample())))
    assert set(z.namelist()) == {"data.json", "audit_log.jsonl", "vendor_price_history.csv", "orders.csv", "upload_queue.jsonl"}


def test_parse_response_extracts_text_and_actions():
    content = [
        SimpleNamespace(type="text", text="Reorder beef."),
        SimpleNamespace(type="tool_use", name="propose_actions",
                        input={"actions": [{"type": "record_sale", "amount": 5}]}),
    ]
    r = parse_response(content)
    assert r.text == "Reorder beef." and r.actions == [{"type": "record_sale", "amount": 5}]


def test_ask_builds_request_and_uses_history():
    captured = {}

    class FakeClient:
        class messages:
            @staticmethod
            def create(**kw):
                captured.update(kw)
                return SimpleNamespace(content=[SimpleNamespace(type="text", text="ok")])

    r = ask(FakeClient, "m", "q?", "STATE", [("You", "hi"), ("AI", "hello")])
    assert r.text == "ok"
    assert [x["role"] for x in captured["messages"]] == ["user", "assistant", "user"]
    assert "STATE" in captured["messages"][-1]["content"]
    assert captured["tools"][0]["name"] == "propose_actions"
