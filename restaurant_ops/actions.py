"""Validate and apply AI-proposed actions.

The action set is deliberately narrow: local state changes only, and every
action is applied only after the user approves it in the UI.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from .manager import RestaurantManager
from .storage import Store

ACTION_TYPES = ["set_hours", "update_menu_price", "add_vendor_price", "record_sale", "record_expense"]

_REQUIRED = {
    "set_hours": ["hours"],
    "update_menu_price": ["item", "price"],
    "add_vendor_price": ["vendor", "item", "price"],
    "record_sale": ["amount"],
    "record_expense": ["amount"],
}


def _num(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def validate_action(a: Dict[str, Any]) -> str | None:
    """Return an error string, or None if the action is valid."""
    if not isinstance(a, dict):
        return "action is not an object"
    t = a.get("type")
    if t not in _REQUIRED:
        return f"unknown action type: {t!r}"
    for key in _REQUIRED[t]:
        if key in ("price", "amount"):
            v = _num(a.get(key))
            if v is None or v <= 0:
                return f"{t}: {key} must be a positive number"
        elif not str(a.get(key, "")).strip():
            return f"{t}: missing {key}"
    return None


def describe_action(a: Dict[str, Any]) -> str:
    t = a.get("type")
    if t == "set_hours":
        return f"Set hours on all platforms to {a.get('hours')}"
    if t == "update_menu_price":
        return f"Set {a.get('item')} to ${_num(a.get('price')) or 0:.2f} on all platforms"
    if t == "add_vendor_price":
        return f"Record {a.get('vendor')} price for {a.get('item')}: ${_num(a.get('price')) or 0:.2f}"
    if t == "record_sale":
        return f"Record sale of ${_num(a.get('amount')) or 0:.2f}"
    if t == "record_expense":
        return f"Record expense of ${_num(a.get('amount')) or 0:.2f}"
    return str(a)


def execute_actions(m: RestaurantManager, store: Store, actions: List[Dict[str, Any]]) -> List[str]:
    results: List[str] = []
    for a in actions:
        err = validate_action(a)
        if err:
            results.append(f"Skipped: {err}")
            continue
        t = a["type"]
        if t == "set_hours":
            hours = str(a["hours"]).strip()
            m.set_business_hours(hours)
            store.log("agent_set_hours", {"hours": hours})
        elif t == "update_menu_price":
            item, price = str(a["item"]).strip(), float(a["price"])
            m.update_menu_item(item, price)
            store.log("agent_update_menu_price", {"item": item, "price": price})
        elif t == "add_vendor_price":
            vendor, item, price = str(a["vendor"]).strip(), str(a["item"]).strip(), float(a["price"])
            m.set_vendor_price(vendor, item, price)
            store.append_vendor_history(vendor, item, price)
            store.log("agent_add_vendor_price", {"vendor": vendor, "item": item, "price": price})
        elif t == "record_sale":
            m.record_sale(float(a["amount"]))
            store.log("agent_record_sale", {"amount": float(a["amount"])})
        elif t == "record_expense":
            m.record_expense(float(a["amount"]))
            store.log("agent_record_expense", {"amount": float(a["amount"])})
        results.append(f"Applied: {describe_action(a)}")
    return results
