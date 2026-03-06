import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

import pandas as pd
import requests
import streamlit as st

from restaurant_ai_app import RestaurantManager, MaintenanceRequest, JobPosting


DATA_PATH = Path("data.json")
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"


# -------------------------
# Persistence helpers
# -------------------------

def manager_to_dict(m: RestaurantManager) -> Dict[str, Any]:
    return {
        "platforms": [{"name": p.name, "menu": p.menu, "hours": p.hours} for p in m.platforms],
        "vendor_prices": m.vendor_prices,
        "maintenance_requests": [{"description": r.description, "contact": r.contact} for r in m.maintenance_requests],
        "job_postings": [{"action": j.action, "position": j.position, "boards": j.boards} for j in m.job_postings],
        "revenue": m.revenue,
        "expenses": m.expenses,
    }


def load_manager() -> RestaurantManager:
    m = RestaurantManager()

    if not DATA_PATH.exists():
        # Sample defaults
        m.add_platform("POS", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
        m.add_platform("Website", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
        m.add_platform("DeliveryApp", {"Burger": 11.99, "Fries": 4.49}, "10am–9pm")

        m.add_vendor_prices("VendorA", {"Grenadine": 12.00, "Plastic Cups": 8.50, "Beef": 5.25})
        m.add_vendor_prices("VendorB", {"Grenadine": 11.50, "Plastic Cups": 9.00, "Beef": 5.75, "Wine": 14.00})
        m.add_vendor_prices("VendorC", {"Grenadine": 12.25, "Plastic Cups": 8.00, "Beef": 5.50, "Wine": 13.50})
        return m

    data = json.loads(DATA_PATH.read_text())
    for p in data.get("platforms", []):
        m.add_platform(p["name"], p.get("menu", {}), p.get("hours", ""))

    m.vendor_prices = data.get("vendor_prices", {})

    m.maintenance_requests = [MaintenanceRequest(**r) for r in data.get("maintenance_requests", [])]
    m.job_postings = [JobPosting(**j) for j in data.get("job_postings", [])]

    m.revenue = [float(x) for x in data.get("revenue", [])]
    m.expenses = [float(x) for x in data.get("expenses", [])]
    return m


def save_manager(m: RestaurantManager) -> None:
    DATA_PATH.write_text(json.dumps(manager_to_dict(m), indent=2))


# -------------------------
# Ollama helper
# -------------------------

def qwen_answer(prompt: str) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    return r.json().get("response", "").strip()


# -------------------------
# Streamlit UI
# -------------------------

st.set_page_config(page_title="Restaurant Ops Dashboard", layout="wide")
st.title("Restaurant Ops Dashboard")

if "manager" not in st.session_state:
    st.session_state.manager = load_manager()

manager: RestaurantManager = st.session_state.manager

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("Save data", width="stretch"):
        save_manager(manager)
        st.success("Saved")
with col2:
    if st.button("Reload", width="stretch"):
        st.session_state.manager = load_manager()
        st.rerun()
with col3:
    st.caption(f"Data file: {DATA_PATH.resolve()}")

tabs = st.tabs(["Platforms", "Menu", "Hours", "Vendors", "Weekly Order", "Maintenance", "Hiring", "Finance", "AI Assistant"])

# -------------------------
# Platforms
# -------------------------
with tabs[0]:
    st.header("Platforms")
    rows = [{"Platform": p.name, "Hours": p.hours, "Menu Items": len(p.menu)} for p in manager.platforms]
    st.dataframe(pd.DataFrame(rows), width="stretch")

    st.subheader("Add platform")
    new_name = st.text_input("Platform name", placeholder="e.g., Toast POS, Website, DoorDash", key="plat_name")
    new_hours = st.text_input("Hours", placeholder="e.g., 11am–9pm", key="plat_hours")
    if st.button("Add", key="plat_add"):
        if new_name.strip():
            manager.add_platform(new_name.strip(), {}, new_hours.strip())
            st.success("Platform added")
        else:
            st.error("Platform name required")

# -------------------------
# Menu
# -------------------------
with tabs[1]:
    st.header("Menu")
    all_items = {}
    for p in manager.platforms:
        for k, v in p.menu.items():
            all_items.setdefault(k, []).append((p.name, v))

    items = [{"Item": k, "Prices": ", ".join([f"{pn}: ${pv:.2f}" for pn, pv in v])} for k, v in all_items.items()]
    st.dataframe(pd.DataFrame(items), width="stretch")

    st.subheader("Update menu item across all platforms")
    item = st.text_input("Item", placeholder="e.g., Fries", key="menu_item")
    price = st.number_input("New price", value=0.0, step=0.25, key="menu_price")
    if st.button("Update price", key="menu_update"):
        if item.strip() and price > 0:
            manager.update_menu_item(item.strip(), float(price))
            st.success("Updated across platforms")
        else:
            st.error("Item and a price > 0 are required")

# -------------------------
# Hours
# -------------------------
with tabs[2]:
    st.header("Hours")
    hours = st.text_input("Set business hours across all platforms", placeholder="e.g., 11am–9pm", key="hours_all")
    if st.button("Update hours", key="hours_update"):
        if hours.strip():
            manager.set_business_hours(hours.strip())
            st.success("Hours updated")
        else:
            st.error("Hours required")

# -------------------------
# Vendors
# -------------------------
with tabs[3]:
    st.header("Vendors")
    vendor_names = sorted(manager.vendor_prices.keys())
    st.write("Current vendors:", ", ".join(vendor_names) if vendor_names else "None")

    st.subheader("Add/Update vendor price list")
    vname = st.text_input("Vendor name", placeholder="e.g., VendorA", key="vendor_name")
    raw = st.text_area("Prices (one per line: item=price)", placeholder="Beef=5.25\nWine=13.50", key="vendor_prices")
    if st.button("Save vendor prices", key="vendor_save"):
        if not vname.strip():
            st.error("Vendor name required")
        else:
            prices = {}
            for line in raw.splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                try:
                    prices[k] = float(v.strip())
                except ValueError:
                    st.error(f"Bad price line: {line}")
                    prices = None
                    break
            if prices is not None:
                manager.add_vendor_prices(vname.strip(), prices)
                st.success("Vendor prices saved")

# -------------------------
# Weekly Order
# -------------------------
with tabs[4]:
    st.header("Weekly Order")
    items = st.text_area("Items (one per line)", placeholder="Grenadine\nPlastic Cups\nBeef\nWine", key="order_items")
    if st.button("Compile weekly order", key="order_compile"):
        req_items = [x.strip() for x in items.splitlines() if x.strip()]
        if not req_items:
            st.error("Add at least one item")
        else:
            order = manager.compile_weekly_order(req_items)
            out_rows = []
            for vendor, lst in order.items():
                for it, pr in lst:
                    out_rows.append({"Vendor": vendor, "Item": it, "Price": pr})
            st.dataframe(pd.DataFrame(out_rows), width="stretch")

# -------------------------
# Maintenance
# -------------------------
with tabs[5]:
    st.header("Maintenance")
    m_rows = [{"Issue": r.description, "Contact": r.contact} for r in manager.maintenance_requests]
    st.dataframe(pd.DataFrame(m_rows), width="stretch")

    st.subheader("Log maintenance issue")
    desc = st.text_input("Issue", placeholder="Walk-in cooler not cooling", key="mnt_desc")
    contact = st.text_input("Who to notify", placeholder="Refrigeration contractor", key="mnt_contact")
    if st.button("Log issue", key="mnt_log"):
        if desc.strip() and contact.strip():
            manager.report_maintenance_issue(desc.strip(), contact.strip())
            st.success("Logged")
        else:
            st.error("Issue and contact required")

# -------------------------
# Hiring
# -------------------------
with tabs[6]:
    st.header("Hiring / Termination")
    j_rows = [{"Action": j.action, "Position": j.position, "Boards": ", ".join(j.boards)} for j in manager.job_postings]
    st.dataframe(pd.DataFrame(j_rows), width="stretch")

    st.subheader("Post job update")
    action = st.selectbox("Action", ["hire", "fire"], key="job_action")
    position = st.text_input("Position", placeholder="Line Cook", key="job_position")
    boards = st.text_input("Boards (comma separated)", placeholder="Indeed, Craigslist, Company Site", key="job_boards")
    if st.button("Post update", key="job_post"):
        b = [x.strip() for x in boards.split(",") if x.strip()]
        if position.strip() and b:
            manager.post_job_update(action, position.strip(), b)
            st.success("Posted (demo)")
        else:
            st.error("Position and at least one board required")

# -------------------------
# Finance
# -------------------------
with tabs[7]:
    st.header("Finance")
    st.subheader("Revenue")
    sale = st.number_input("Add sale", value=0.0, step=10.0, key="fin_sale")
    if st.button("Record sale", key="fin_sale_btn"):
        if sale > 0:
            manager.record_sale(float(sale))
            st.success("Revenue recorded")
        else:
            st.error("Sale must be > 0")

    st.subheader("Expenses")
    expense = st.number_input("Add expense", value=0.0, step=10.0, key="fin_expense")
    if st.button("Record expense", key="fin_exp_btn"):
        if expense > 0:
            manager.record_expense(float(expense))
            st.success("Expense recorded")
        else:
            st.error("Expense must be > 0")

    st.divider()
    st.subheader("Profit & Loss")
    if st.button("Generate P&L", key="fin_pnl"):
        rev, exp, profit = manager.generate_pnl()
        st.metric("Revenue", f"${rev:.2f}")
        st.metric("Expenses", f"${exp:.2f}")
        st.metric("Profit", f"${profit:.2f}")

# -------------------------
# AI Assistant
# -------------------------
with tabs[8]:
    st.header("AI Assistant (Qwen)")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    question = st.text_input("Ask the AI about your restaurant", key="ai_q")

    if st.button("Ask AI", key="ai_ask"):
        if question.strip():
            try:
                prompt = f"""
You are an assistant helping manage a restaurant.

Current totals:
Revenue: {sum(manager.revenue):.2f}
Expenses: {sum(manager.expenses):.2f}
Profit: {(sum(manager.revenue) - sum(manager.expenses)):.2f}

Question:
{question}

Answer clearly and concisely.
""".strip()

                with st.spinner("Thinking..."):
                    answer = qwen_answer(prompt)

                st.session_state.chat_history.append(("You", question))
                st.session_state.chat_history.append(("AI", answer))

            except Exception as e:
                st.error(f"AI error: {e}")

    for role, msg in st.session_state.chat_history:
        st.markdown(f"**{role}:** {msg}")
