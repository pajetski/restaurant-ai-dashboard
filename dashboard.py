import json
import io
import csv
import zipfile
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

from restaurant_ai_app import RestaurantManager, MaintenanceRequest, JobPosting, Platform

# ----------------------------
# Paths / Config
# ----------------------------
APP_TITLE = "Restaurant Ops Dashboard"
DATA_PATH = Path("data.json")
UPLOAD_DIR = Path("uploads")
AUDIT_PATH = Path("audit_log.jsonl")
VENDOR_HISTORY_PATH = Path("vendor_price_history.csv")

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:7b"

# ----------------------------
# Helpers
# ----------------------------
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def log_action(action: str, payload: Dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"time": now_iso(), "action": action, "payload": payload}
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_audit(limit: int = 200) -> pd.DataFrame:
    if not AUDIT_PATH.exists():
        return pd.DataFrame(columns=["time", "action", "payload"])
    rows = []
    with AUDIT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["time", "action", "payload"])
    # newest first
    df = df.sort_values("time", ascending=False).head(limit)
    return df


def manager_to_dict(m: RestaurantManager) -> Dict[str, Any]:
    return {
        "platforms": [{"name": p.name, "menu": p.menu, "hours": p.hours} for p in m.platforms],
        "vendor_prices": m.vendor_prices,
        "maintenance_requests": [{"description": r.description, "contact": r.contact} for r in m.maintenance_requests],
        "job_postings": [{"action": j.action, "position": j.position, "boards": j.boards} for j in m.job_postings],
        "revenue": m.revenue,
        "expenses": m.expenses,
        # optional: store simple order log (if you start capturing)
        "orders": st.session_state.get("orders", []),
    }


def dict_to_manager(d: Dict[str, Any]) -> RestaurantManager:
    m = RestaurantManager()
    for p in d.get("platforms", []):
        m.add_platform(p["name"], p.get("menu", {}), p.get("hours", ""))
    m.vendor_prices = d.get("vendor_prices", {}) or {}
    m.maintenance_requests = [MaintenanceRequest(**r) for r in d.get("maintenance_requests", [])]
    m.job_postings = [JobPosting(**j) for j in d.get("job_postings", [])]
    m.revenue = [float(x) for x in d.get("revenue", [])]
    m.expenses = [float(x) for x in d.get("expenses", [])]
    st.session_state["orders"] = d.get("orders", [])
    return m


def load_manager() -> RestaurantManager:
    if DATA_PATH.exists():
        try:
            data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
            return dict_to_manager(data)
        except Exception:
            pass

    # sample defaults if no file
    m = RestaurantManager()
    m.add_platform("POS", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
    m.add_platform("Website", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
    m.add_platform("DeliveryApp", {"Burger": 11.99, "Fries": 4.49}, "10am–9pm")

    m.add_vendor_prices("VendorA", {"Grenadine": 12.00, "Plastic Cups": 8.50, "Beef": 5.25})
    m.add_vendor_prices("VendorB", {"Grenadine": 11.50, "Plastic Cups": 9.00, "Beef": 5.75, "Wine": 14.00})
    m.add_vendor_prices("VendorC", {"Grenadine": 12.25, "Plastic Cups": 8.00, "Beef": 5.50, "Wine": 13.50})

    st.session_state["orders"] = []
    return m


def save_manager(m: RestaurantManager) -> None:
    DATA_PATH.write_text(json.dumps(manager_to_dict(m), indent=2), encoding="utf-8")
    log_action("save_data", {"path": str(DATA_PATH)})


def reset_sample() -> RestaurantManager:
    if DATA_PATH.exists():
        try:
            DATA_PATH.unlink()
        except Exception:
            pass
    log_action("reset_sample", {})
    return load_manager()


def ensure_vendor_history_schema() -> None:
    if VENDOR_HISTORY_PATH.exists():
        return
    with VENDOR_HISTORY_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "vendor", "item", "price"])


def append_vendor_history(vendor: str, item: str, price: float) -> None:
    ensure_vendor_history_schema()
    with VENDOR_HISTORY_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([now_iso(), vendor, item, f"{price:.4f}"])


def load_vendor_history() -> pd.DataFrame:
    if not VENDOR_HISTORY_PATH.exists():
        return pd.DataFrame(columns=["time", "vendor", "item", "price"])
    try:
        df = pd.read_csv(VENDOR_HISTORY_PATH)
        return df
    except Exception:
        return pd.DataFrame(columns=["time", "vendor", "item", "price"])


def detect_cost_creep(df: pd.DataFrame, lookback_rows: int = 2000) -> pd.DataFrame:
    """
    Simple cost-creep detector:
    For each vendor+item, compare latest price vs previous price.
    """
    if df.empty:
        return pd.DataFrame(columns=["vendor", "item", "prev_price", "latest_price", "delta", "delta_pct", "time"])
    df2 = df.tail(lookback_rows).copy()
    df2["price"] = pd.to_numeric(df2["price"], errors="coerce")
    df2 = df2.dropna(subset=["price"])
    df2 = df2.sort_values("time")
    # get latest and prev
    out = []
    for (vendor, item), g in df2.groupby(["vendor", "item"], dropna=False):
        if len(g) < 2:
            continue
        prev = g.iloc[-2]
        latest = g.iloc[-1]
        prev_p = float(prev["price"])
        latest_p = float(latest["price"])
        delta = latest_p - prev_p
        delta_pct = (delta / prev_p) * 100.0 if prev_p != 0 else None
        out.append(
            {
                "vendor": vendor,
                "item": item,
                "prev_price": prev_p,
                "latest_price": latest_p,
                "delta": delta,
                "delta_pct": delta_pct,
                "time": latest["time"],
            }
        )
    res = pd.DataFrame(out)
    if res.empty:
        return res
    res = res.sort_values(["delta_pct", "delta"], ascending=False)
    return res


def ollama_generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "").strip()


def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def parse_actions_json(text: str) -> Dict[str, Any]:
    """
    Expect model to return JSON (possibly inside ```json fences).
    """
    t = text.strip()
    if t.startswith("```"):
        # remove fences
        t = t.replace("```json", "").replace("```", "").strip()
    return json.loads(t)


def build_context_summary(m: RestaurantManager) -> str:
    # short, stable business context (keeps prompt size sane)
    platforms = ", ".join([p.name for p in m.platforms]) if m.platforms else "none"
    menu_items = sorted({k for p in m.platforms for k in p.menu.keys()})
    menu_preview = ", ".join(menu_items[:20]) + ("..." if len(menu_items) > 20 else "")
    rev = sum(m.revenue)
    exp = sum(m.expenses)
    profit = rev - exp
    return (
        f"Platforms: {platforms}\n"
        f"Menu items: {menu_preview if menu_preview else 'none'}\n"
        f"Revenue total: {rev:.2f}\n"
        f"Expenses total: {exp:.2f}\n"
        f"Profit total: {profit:.2f}\n"
        f"Vendors tracked: {', '.join(m.vendor_prices.keys()) if m.vendor_prices else 'none'}\n"
    )


def execute_actions(m: RestaurantManager, actions: List[Dict[str, Any]]) -> List[str]:
    """
    Minimal “Action Agent” executor.
    We intentionally keep actions narrow + safe (no OS commands, no network writes beyond local json).
    """
    results = []
    for a in actions:
        atype = a.get("type")
        try:
            if atype == "set_hours":
                hours = str(a.get("hours", "")).strip()
                if not hours:
                    results.append("Skipped set_hours (missing hours).")
                    continue
                for p in m.platforms:
                    p.set_hours(hours)
                results.append(f"Set hours on all platforms to: {hours}")
                log_action("agent_set_hours", {"hours": hours})

            elif atype == "update_menu_price":
                item = str(a.get("item", "")).strip()
                price = safe_float(a.get("price"))
                if not item or price is None:
                    results.append("Skipped update_menu_price (missing item or price).")
                    continue
                for p in m.platforms:
                    p.update_menu_item(item, float(price))
                results.append(f"Updated menu price: {item} = ${float(price):.2f} across platforms")
                log_action("agent_update_menu_price", {"item": item, "price": float(price)})

            elif atype == "add_vendor_price":
                vendor = str(a.get("vendor", "")).strip()
                item = str(a.get("item", "")).strip()
                price = safe_float(a.get("price"))
                if not vendor or not item or price is None:
                    results.append("Skipped add_vendor_price (missing vendor/item/price).")
                    continue
                if vendor not in m.vendor_prices:
                    m.vendor_prices[vendor] = {}
                m.vendor_prices[vendor][item] = float(price)
                append_vendor_history(vendor, item, float(price))
                results.append(f"Saved vendor price: {vendor} → {item} = ${float(price):.2f}")
                log_action("agent_add_vendor_price", {"vendor": vendor, "item": item, "price": float(price)})

            elif atype == "record_sale":
                amt = safe_float(a.get("amount"))
                if amt is None or amt <= 0:
                    results.append("Skipped record_sale (invalid amount).")
                    continue
                m.revenue.append(float(amt))
                results.append(f"Recorded sale: ${float(amt):.2f}")
                log_action("agent_record_sale", {"amount": float(amt)})

            elif atype == "record_expense":
                amt = safe_float(a.get("amount"))
                if amt is None or amt <= 0:
                    results.append("Skipped record_expense (invalid amount).")
                    continue
                m.expenses.append(float(amt))
                results.append(f"Recorded expense: ${float(amt):.2f}")
                log_action("agent_record_expense", {"amount": float(amt)})

            else:
                results.append(f"Unknown action type: {atype}")
        except Exception as e:
            results.append(f"Action failed ({atype}): {e}")
    return results


def export_zip(m: RestaurantManager) -> bytes:
    """
    ZIP for accountants / ops:
    - data.json
    - audit_log.jsonl
    - vendor_price_history.csv
    - orders.csv (if present)
    """
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("data.json", json.dumps(manager_to_dict(m), indent=2))

        if AUDIT_PATH.exists():
            z.writestr("audit_log.jsonl", AUDIT_PATH.read_text(encoding="utf-8"))
        else:
            z.writestr("audit_log.jsonl", "")

        if VENDOR_HISTORY_PATH.exists():
            z.writestr("vendor_price_history.csv", VENDOR_HISTORY_PATH.read_text(encoding="utf-8"))
        else:
            z.writestr("vendor_price_history.csv", "time,vendor,item,price\n")

        # Orders
        orders = st.session_state.get("orders", [])
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["time", "platform", "item", "qty"])
        for o in orders:
            w.writerow([o.get("time"), o.get("platform"), o.get("item"), o.get("qty")])
        z.writestr("orders.csv", out.getvalue())

        # Upload index (if exists)
        upload_index = Path("upload_queue.jsonl")
        if upload_index.exists():
            z.writestr("upload_queue.jsonl", upload_index.read_text(encoding="utf-8"))
        else:
            z.writestr("upload_queue.jsonl", "")

    mem.seek(0)
    return mem.read()


UPLOAD_QUEUE_PATH = Path("upload_queue.jsonl")


def enqueue_upload(meta: Dict[str, Any]) -> None:
    UPLOAD_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with UPLOAD_QUEUE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")


# ----------------------------
# Page
# ----------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# Load manager once per session
if "manager" not in st.session_state:
    st.session_state.manager = load_manager()

manager: RestaurantManager = st.session_state.manager

# Top actions
c1, c2, c3, c4 = st.columns([1, 1, 1.4, 2.6])
with c1:
    if st.button("Save data", width="stretch"):
        save_manager(manager)
        st.success("Saved.")
with c2:
    if st.button("Reload", width="stretch"):
        st.session_state.manager = load_manager()
        manager = st.session_state.manager
        st.success("Reloaded.")
with c3:
    if st.button("Reset to sample (no save)", width="stretch"):
        st.session_state.manager = reset_sample()
        manager = st.session_state.manager
        st.success("Reset.")
with c4:
    st.caption(f"Data file: {DATA_PATH.resolve()}")

st.divider()

# ----------------------------
# Tabs
# ----------------------------
tabs = st.tabs(
    [
        "Platforms",
        "Menu",
        "Hours",
        "Vendors",
        "Weekly Order",
        "Maintenance",
        "Hiring",
        "Finance",
        "AI Ops",
        "Audit & Export",
    ]
)

# ----------------------------
# Platforms
# ----------------------------
with tabs[0]:
    st.header("Platforms")
    st.caption("Registered platforms and current hours.")

    plat_rows = []
    for p in manager.platforms:
        plat_rows.append({"Platform": p.name, "Hours": p.hours, "Menu Items": len(p.menu)})
    dfp = pd.DataFrame(plat_rows) if plat_rows else pd.DataFrame(columns=["Platform", "Hours", "Menu Items"])
    st.dataframe(dfp, width="stretch", hide_index=True)

    st.subheader("Add platform")
    name = st.text_input("Platform name", placeholder="e.g., Toast POS, Website, DoorDash", key="add_plat_name")
    hours = st.text_input("Hours", placeholder="e.g., 11am–9pm", key="add_plat_hours")
    if st.button("Add", key="add_plat_btn"):
        if name.strip():
            manager.add_platform(name.strip(), {}, hours.strip())
            log_action("add_platform", {"name": name.strip(), "hours": hours.strip()})
            st.success("Added.")
        else:
            st.error("Platform name required.")

# ----------------------------
# Menu
# ----------------------------
with tabs[1]:
    st.header("Menu")
    st.caption("Edit menu items. Changes apply to all platforms.")

    all_items = sorted({k for p in manager.platforms for k in p.menu.keys()})
    colA, colB, colC = st.columns([1.2, 1, 1])
    with colA:
        item = st.selectbox("Menu item", options=(all_items if all_items else ["(none yet)"]), key="menu_item")
    with colB:
        new_item = st.text_input("Or new item", placeholder="e.g., Margarita", key="new_menu_item")
    with colC:
        price = st.number_input("Price", min_value=0.0, value=0.0, step=0.25, key="menu_price")

    if st.button("Set price across platforms", key="menu_set_price"):
        chosen = new_item.strip() if new_item.strip() else item
        if not chosen or chosen == "(none yet)":
            st.error("Choose or enter a menu item.")
        else:
            for p in manager.platforms:
                p.update_menu_item(chosen, float(price))
            log_action("set_menu_price", {"item": chosen, "price": float(price)})
            st.success(f"Updated {chosen} to ${price:.2f} across platforms.")

    # show consolidated menu (average if inconsistent)
    st.subheader("Current consolidated menu")
    rows = []
    for it in sorted({k for p in manager.platforms for k in p.menu.keys()}):
        prices = [p.menu.get(it) for p in manager.platforms if it in p.menu]
        rows.append({"Item": it, "Prices (by platform)": prices})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# ----------------------------
# Hours
# ----------------------------
with tabs[2]:
    st.header("Hours")
    st.caption("Set business hours across all platforms.")
    hours = st.text_input("Hours", placeholder="e.g., 11am–9pm", key="hours_all")
    if st.button("Apply hours to all platforms", key="hours_apply"):
        if hours.strip():
            for p in manager.platforms:
                p.set_hours(hours.strip())
            log_action("set_hours_all", {"hours": hours.strip()})
            st.success("Updated hours.")
        else:
            st.error("Enter hours.")

# ----------------------------
# Vendors
# ----------------------------
with tabs[3]:
    st.header("Vendors")
    st.caption("Track vendor prices and history (detects cost creep).")

    vendor = st.text_input("Vendor", placeholder="e.g., US Foods", key="vendor_name")
    item = st.text_input("Item", placeholder="e.g., Beef", key="vendor_item")
    price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01, key="vendor_price")
    if st.button("Save vendor price", key="vendor_save"):
        if vendor.strip() and item.strip() and price > 0:
            manager.vendor_prices.setdefault(vendor.strip(), {})[item.strip()] = float(price)
            append_vendor_history(vendor.strip(), item.strip(), float(price))
            log_action("vendor_price_update", {"vendor": vendor.strip(), "item": item.strip(), "price": float(price)})
            st.success("Saved.")
        else:
            st.error("Vendor, item, and a price > 0 are required.")

    st.subheader("Current vendor prices")
    rows = []
    for v, plist in (manager.vendor_prices or {}).items():
        for it, pr in (plist or {}).items():
            rows.append({"Vendor": v, "Item": it, "Price": pr})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.subheader("Vendor price history + cost creep")
    hist = load_vendor_history()
    st.dataframe(hist.tail(200), width="stretch", hide_index=True)

    creep = detect_cost_creep(hist)
    if creep.empty:
        st.info("No cost-creep signals yet (need at least two price points per vendor+item).")
    else:
        st.warning("Potential cost creep (latest vs previous):")
        st.dataframe(creep.head(50), width="stretch", hide_index=True)

# ----------------------------
# Weekly Order
# ----------------------------
with tabs[4]:
    st.header("Weekly Order")
    st.caption("Pick items and get lowest-cost vendor per item.")

    items = sorted({k for v in (manager.vendor_prices or {}).values() for k in (v or {}).keys()})
    chosen = st.multiselect("Items to order", options=items, key="weekly_items")
    if st.button("Compare & compile order", key="weekly_compile"):
        if not chosen:
            st.error("Select at least one item.")
        else:
            # use RestaurantManager logic
            res = manager.compare_prices(chosen)
            order: Dict[str, List[Tuple[str, float]]] = {}
            for it, (vend, pr) in res.items():
                order.setdefault(vend, []).append((it, pr))

            st.subheader("Recommended order (by vendor)")
            for vend, items_list in order.items():
                subtotal = sum(p for _, p in items_list)
                st.write(f"**{vend}** — subtotal ${subtotal:.2f}")
                st.dataframe(pd.DataFrame(items_list, columns=["Item", "Price"]), width="stretch", hide_index=True)

            log_action("compile_weekly_order", {"items": chosen, "vendors": list(order.keys())})

# ----------------------------
# Maintenance
# ----------------------------
with tabs[5]:
    st.header("Maintenance")
    desc = st.text_input("Issue description", placeholder="e.g., Walk-in cooler not cooling", key="maint_desc")
    contact = st.text_input("Contact / vendor", placeholder="e.g., Refrigeration contractor", key="maint_contact")
    if st.button("Log maintenance issue", key="maint_log"):
        if desc.strip() and contact.strip():
            manager.maintenance_requests.append(MaintenanceRequest(description=desc.strip(), contact=contact.strip()))
            log_action("maintenance_log", {"description": desc.strip(), "contact": contact.strip()})
            st.success("Logged.")
        else:
            st.error("Description and contact required.")

    st.subheader("Open requests")
    st.dataframe(
        pd.DataFrame([r.__dict__ for r in manager.maintenance_requests]),
        width="stretch",
        hide_index=True,
    )

# ----------------------------
# Hiring
# ----------------------------
with tabs[6]:
    st.header("Hiring / HR")
    action = st.selectbox("Action", options=["hire", "fire"], key="hr_action")
    position = st.text_input("Position", placeholder="e.g., Line Cook", key="hr_position")
    boards = st.text_input("Boards (comma-separated)", placeholder="Indeed, Craigslist, Company Site", key="hr_boards")
    if st.button("Record HR update", key="hr_record"):
        b = [x.strip() for x in boards.split(",") if x.strip()]
        if position.strip() and b:
            manager.job_postings.append(JobPosting(action=action, position=position.strip(), boards=b))
            log_action("hr_update", {"action": action, "position": position.strip(), "boards": b})
            st.success("Recorded.")
        else:
            st.error("Position and at least one board required.")

    st.subheader("History")
    st.dataframe(pd.DataFrame([j.__dict__ for j in manager.job_postings]), width="stretch", hide_index=True)

# ----------------------------
# Finance
# ----------------------------
with tabs[7]:
    st.header("Finance")
    st.caption("Simple revenue/expense tracking + P&L.")

    cA, cB = st.columns(2)
    with cA:
        st.subheader("Revenue")
        sale = st.number_input("Add sale", min_value=0.0, value=0.0, step=10.0, key="sale_amt")
        if st.button("Record sale", key="sale_btn"):
            if sale > 0:
                manager.revenue.append(float(sale))
                log_action("record_sale", {"amount": float(sale)})
                st.success("Recorded.")
            else:
                st.error("Sale must be > 0")
    with cB:
        st.subheader("Expenses")
        expense = st.number_input("Add expense", min_value=0.0, value=0.0, step=10.0, key="exp_amt")
        if st.button("Record expense", key="exp_btn"):
            if expense > 0:
                manager.expenses.append(float(expense))
                log_action("record_expense", {"amount": float(expense)})
                st.success("Recorded.")
            else:
                st.error("Expense must be > 0")

    st.divider()
    st.subheader("Profit & Loss")
    rev = sum(manager.revenue)
    exp = sum(manager.expenses)
    prof = rev - exp
    m1, m2, m3 = st.columns(3)
    m1.metric("Revenue", f"${rev:,.2f}")
    m2.metric("Expenses", f"${exp:,.2f}")
    m3.metric("Profit", f"${prof:,.2f}")

# ----------------------------
# AI Ops (Speech bubble + Upload)
# ----------------------------
with tabs[8]:
    st.header("AI Ops")

    left, right = st.columns([1.15, 0.85], gap="large")

    # ---------------- Speech bubble chat ----------------
    with left:
        # speech-bubble style container
        st.markdown(
            """
            <div style="
                border:1px solid rgba(255,255,255,0.12);
                background: rgba(255,255,255,0.03);
                padding: 18px;
                border-radius: 14px;
                position: relative;
            ">
              <div style="font-size: 18px; font-weight: 700; margin-bottom: 6px;">
                Ask me things about your restaurant
              </div>
              <div style="opacity: 0.8; margin-bottom: 12px;">
                Try: <b>What should I reorder this week?</b>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        model = st.text_input("Model", value=DEFAULT_MODEL, key="ai_model")
        question = st.text_input("Your question", placeholder="What should I reorder this week?", key="ai_question")

        def build_ai_prompt(user_q: str) -> str:
            ctx = build_context_summary(manager)
            vendor_hist = load_vendor_history().tail(50)
            creep = detect_cost_creep(load_vendor_history()).head(20)
            return (
                "You are an AI operations assistant for a restaurant.\n"
                "Goal: give actionable ops guidance (inventory, ordering, staffing, pricing).\n"
                "If uncertain, ask ONE clarifying question.\n\n"
                "CURRENT STATE\n"
                f"{ctx}\n"
                "VENDOR HISTORY (recent rows)\n"
                f"{vendor_hist.to_csv(index=False) if not vendor_hist.empty else 'none'}\n"
                "COST CREEP SIGNALS\n"
                f"{creep.to_csv(index=False) if not creep.empty else 'none'}\n\n"
                "When appropriate, output a JSON block with suggested actions.\n"
                "Allowed actions:\n"
                "- set_hours: {type:'set_hours', hours:'11am–9pm'}\n"
                "- update_menu_price: {type:'update_menu_price', item:'Fries', price:3.99}\n"
                "- add_vendor_price: {type:'add_vendor_price', vendor:'VendorA', item:'Beef', price:5.25}\n"
                "- record_sale: {type:'record_sale', amount:1500}\n"
                "- record_expense: {type:'record_expense', amount:500}\n\n"
                "RESPONSE FORMAT\n"
                "1) Plain-English answer.\n"
                "2) OPTIONAL JSON on its own line (or fenced) like:\n"
                "{\"actions\":[{...}]}\n\n"
                f"USER QUESTION: {user_q}\n"
            )

        ask_col, act_col = st.columns([1, 1])
        with ask_col:
            if st.button("Ask AI", key="ai_ask_btn", width="stretch"):
                if not question.strip():
                    st.error("Ask a question.")
                else:
                    prompt = build_ai_prompt(question.strip())
                    with st.spinner("Thinking..."):
                        try:
                            answer = ollama_generate(prompt, model=model.strip() or DEFAULT_MODEL)
                            st.session_state.chat_history.append(("You", question.strip()))
                            st.session_state.chat_history.append(("AI", answer))
                            log_action("ai_ask", {"question": question.strip(), "model": model.strip()})
                        except Exception as e:
                            st.error(f"AI error: {e}")

        with act_col:
            if st.button("Approve suggested actions (if any)", key="ai_apply_btn", width="stretch"):
                # find latest AI message with JSON
                ai_msgs = [m for role, m in st.session_state.chat_history if role == "AI"]
                if not ai_msgs:
                    st.warning("No AI responses yet.")
                else:
                    latest = ai_msgs[-1]
                    # attempt to extract JSON by scanning for first '{' to last '}'
                    try:
                        s = latest
                        start = s.find("{")
                        end = s.rfind("}")
                        if start == -1 or end == -1 or end <= start:
                            st.warning("No JSON actions found in the latest AI response.")
                        else:
                            candidate = s[start : end + 1]
                            obj = parse_actions_json(candidate)
                            actions = obj.get("actions", [])
                            if not actions:
                                st.warning("JSON found but no actions listed.")
                            else:
                                results = execute_actions(manager, actions)
                                save_manager(manager)
                                st.success("Applied actions.")
                                st.write(results)
                    except Exception as e:
                        st.error(f"Could not parse/apply actions: {e}")

        st.divider()
        for role, msg in st.session_state.chat_history[-20:]:
            st.markdown(f"**{role}:** {msg}")

    # ---------------- Upload section ----------------
    with right:
        st.subheader("Upload files")

        ingest_choice = st.selectbox(
            "What is this file mostly about?",
            [
                "Auto-detect (recommended)",
                "Menu / pricing",
                "Vendor invoices / price sheets",
                "Inventory counts",
                "Sales reports (daily/weekly/monthly)",
                "Payroll / labor",
                "Other",
            ],
            index=0,
            key="ingest_choice",
        )

        uploaded = st.file_uploader(
            "Upload files",
            type=["pdf", "png", "jpg", "jpeg", "csv", "txt"],
            accept_multiple_files=True,
            key="upload_files",
        )

        # ✅ requested placement: under the uploader
        st.markdown(
            "**Feed me files about your business**\n\n"
            "You can add PDF, JPEG, PNG, etc. The AI will sort it out into the right sections."
        )

        if uploaded:
            UPLOAD_DIR.mkdir(exist_ok=True)
            for f in uploaded:
                content = f.getvalue()
                file_hash = sha256_bytes(content)
                save_path = UPLOAD_DIR / f"{file_hash}_{f.name}"
                save_path.write_bytes(content)

                enqueue_upload(
                    {
                        "time": now_iso(),
                        "filename": f.name,
                        "stored_as": str(save_path),
                        "sha256": file_hash,
                        "size_bytes": len(content),
                        "label": ingest_choice,
                    }
                )

            log_action("upload_files", {"count": len(uploaded), "label": ingest_choice})
            st.success(f"Queued {len(uploaded)} file(s) for ingest.")

# ----------------------------
# Audit & Export
# ----------------------------
with tabs[9]:
    st.header("Audit & Export")

    st.subheader("Audit log")
    adf = load_audit(limit=400)
    st.dataframe(adf, width="stretch", hide_index=True)

    st.subheader("Export")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Download audit_log.jsonl", key="dl_audit", width="stretch"):
            pass
        if AUDIT_PATH.exists():
            st.download_button(
                "Download audit_log.jsonl",
                data=AUDIT_PATH.read_bytes(),
                file_name="audit_log.jsonl",
                mime="application/jsonl",
                key="audit_dl_btn",
                width="stretch",
            )
        else:
            st.info("No audit log yet.")
    with c2:
        if VENDOR_HISTORY_PATH.exists():
            st.download_button(
                "Download vendor_price_history.csv",
                data=VENDOR_HISTORY_PATH.read_bytes(),
                file_name="vendor_price_history.csv",
                mime="text/csv",
                key="vendorhist_dl_btn",
                width="stretch",
            )
        else:
            st.info("No vendor history yet.")
    with c3:
        z = export_zip(manager)
        st.download_button(
            "Download Accountant ZIP",
            data=z,
            file_name=f"restaurant_export_{date.today().isoformat()}.zip",
            mime="application/zip",
            key="zip_dl_btn",
            width="stretch",
        )
        st.caption("Includes data.json, audit log, vendor history, orders.csv, and upload queue index.")

st.caption("Tip: changes are only persisted when you click **Save data** (or the agent auto-saves after applying actions).")
