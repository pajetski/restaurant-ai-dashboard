"""Restaurant Ops Dashboard (Streamlit UI). Business logic lives in restaurant_ops/."""

from __future__ import annotations

import hmac
from datetime import date

import pandas as pd
import streamlit as st

from restaurant_ops.actions import describe_action, execute_actions, validate_action
from restaurant_ops.analytics import detect_cost_creep
from restaurant_ops.config import load_config
from restaurant_ops.llm import ask, build_state_block, make_client
from restaurant_ops.manager import RestaurantManager
from restaurant_ops.storage import Store

APP_TITLE = "Restaurant Ops Dashboard"
MAX_UPLOAD_MB = 20

st.set_page_config(page_title=APP_TITLE, layout="wide")
cfg = load_config()


# ----------------------------
# Auth gate
# ----------------------------
def require_login() -> None:
    if not cfg.app_password:
        if cfg.is_production:
            st.error("APP_PASSWORD must be set when APP_ENV=production.")
            st.stop()
        st.sidebar.warning("No APP_PASSWORD set — the app is open. Fine for local dev only.")
        return
    if st.session_state.get("authed"):
        return
    st.title(APP_TITLE)
    pw = st.text_input("Password", type="password")
    if st.button("Sign in"):
        if hmac.compare_digest(pw.encode(), cfg.app_password.encode()):
            st.session_state.authed = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()


require_login()


@st.cache_resource
def get_store(data_dir: str) -> Store:
    return Store(data_dir)


store = get_store(str(cfg.data_dir))
if "manager" not in st.session_state:
    st.session_state.manager = store.load()
manager: RestaurantManager = st.session_state.manager
log = store.log


def table(rows, columns=None) -> None:
    df = pd.DataFrame(rows) if columns is None else pd.DataFrame(rows, columns=columns)
    st.dataframe(df, width="stretch", hide_index=True)


st.title(APP_TITLE)

c1, c2, c3, c4 = st.columns([1, 1, 1.4, 2.6])
with c1:
    if st.button("Save data", width="stretch"):
        store.save(manager)
        st.success("Saved.")
with c2:
    if st.button("Reload", width="stretch"):
        st.session_state.manager = manager = store.load()
        st.success("Reloaded.")
with c3:
    if st.button("Reset to sample", width="stretch"):
        st.session_state.manager = manager = store.reset()
        st.success("Reset to sample data.")
with c4:
    st.caption(f"Data dir: {store.data_dir.resolve()}")
st.divider()

tabs = st.tabs(["Platforms", "Menu", "Hours", "Vendors", "Weekly Order", "Maintenance",
                "Hiring", "Finance", "AI Ops", "Audit & Export"])

# ---- Platforms ----
with tabs[0]:
    st.header("Platforms")
    table([{"Platform": p.name, "Hours": p.hours, "Menu Items": len(p.menu)} for p in manager.platforms],
          ["Platform", "Hours", "Menu Items"])
    st.subheader("Add platform")
    name = st.text_input("Platform name", placeholder="e.g., Toast POS, Website, DoorDash", key="add_plat_name")
    hours = st.text_input("Hours", placeholder="e.g., 11am–9pm", key="add_plat_hours")
    if st.button("Add", key="add_plat_btn"):
        if not name.strip():
            st.error("Platform name required.")
        elif any(p.name.lower() == name.strip().lower() for p in manager.platforms):
            st.error("A platform with that name already exists.")
        else:
            manager.add_platform(name.strip(), {}, hours.strip())
            log("add_platform", {"name": name.strip(), "hours": hours.strip()})
            st.success("Added.")

# ---- Menu ----
with tabs[1]:
    st.header("Menu")
    st.caption("Edit menu items. Changes apply to all platforms.")
    items = manager.menu_items()
    a, b, c = st.columns([1.2, 1, 1])
    item = a.selectbox("Menu item", options=items or ["(none yet)"], key="menu_item")
    new_item = b.text_input("Or new item", placeholder="e.g., Margarita", key="new_menu_item")
    price = c.number_input("Price", min_value=0.0, value=0.0, step=0.25, key="menu_price")
    if st.button("Set price across platforms", key="menu_set_price"):
        chosen = new_item.strip() or item
        if not chosen or chosen == "(none yet)":
            st.error("Choose or enter a menu item.")
        elif not manager.platforms:
            st.error("Add a platform first.")
        else:
            manager.update_menu_item(chosen, float(price))
            log("set_menu_price", {"item": chosen, "price": float(price)})
            st.success(f"Updated {chosen} to ${price:.2f} across platforms.")
    st.subheader("Current consolidated menu")
    table([{"Item": it, **{p.name: p.menu.get(it) for p in manager.platforms}} for it in manager.menu_items()])

# ---- Hours ----
with tabs[2]:
    st.header("Hours")
    hours_all = st.text_input("Hours", placeholder="e.g., 11am–9pm", key="hours_all")
    if st.button("Apply hours to all platforms", key="hours_apply"):
        if hours_all.strip():
            manager.set_business_hours(hours_all.strip())
            log("set_hours_all", {"hours": hours_all.strip()})
            st.success("Updated hours.")
        else:
            st.error("Enter hours.")

# ---- Vendors ----
with tabs[3]:
    st.header("Vendors")
    st.caption("Track vendor prices and history (detects cost creep).")
    vendor = st.text_input("Vendor", placeholder="e.g., US Foods", key="vendor_name")
    v_item = st.text_input("Item", placeholder="e.g., Beef", key="vendor_item")
    v_price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01, key="vendor_price")
    if st.button("Save vendor price", key="vendor_save"):
        if vendor.strip() and v_item.strip() and v_price > 0:
            manager.set_vendor_price(vendor.strip(), v_item.strip(), float(v_price))
            store.append_vendor_history(vendor.strip(), v_item.strip(), float(v_price))
            log("vendor_price_update", {"vendor": vendor.strip(), "item": v_item.strip(), "price": float(v_price)})
            st.success("Saved.")
        else:
            st.error("Vendor, item, and a price > 0 are required.")
    st.subheader("Current vendor prices")
    table([{"Vendor": v, "Item": i, "Price": p} for v, pl in manager.vendor_prices.items() for i, p in (pl or {}).items()])
    st.subheader("Vendor price history + cost creep")
    hist = store.load_vendor_history()
    table(hist.tail(200))
    creep = detect_cost_creep(hist)
    if creep.empty:
        st.info("No cost-creep signals yet (need at least two price points per vendor+item).")
    else:
        st.warning("Potential cost creep (latest vs previous):")
        table(creep.head(50))

# ---- Weekly Order ----
with tabs[4]:
    st.header("Weekly Order")
    st.caption("Pick items and get lowest-cost vendor per item.")
    chosen_items = st.multiselect("Items to order", options=manager.vendor_items(), key="weekly_items")
    if st.button("Compare & compile order", key="weekly_compile"):
        if not chosen_items:
            st.error("Select at least one item.")
        else:
            order = manager.compile_weekly_order(chosen_items)
            st.subheader("Recommended order (by vendor)")
            for vend, lines in order.items():
                st.write(f"**{vend}** — subtotal ${sum(p for _, p in lines):.2f}")
                table(lines, ["Item", "Price"])
            log("compile_weekly_order", {"items": chosen_items, "vendors": list(order)})

# ---- Maintenance ----
with tabs[5]:
    st.header("Maintenance")
    desc = st.text_input("Issue description", placeholder="e.g., Walk-in cooler not cooling", key="maint_desc")
    contact = st.text_input("Contact / vendor", placeholder="e.g., Refrigeration contractor", key="maint_contact")
    if st.button("Log maintenance issue", key="maint_log"):
        if desc.strip() and contact.strip():
            manager.report_maintenance_issue(desc.strip(), contact.strip())
            log("maintenance_log", {"description": desc.strip(), "contact": contact.strip()})
            st.success("Logged.")
        else:
            st.error("Description and contact required.")
    st.subheader("Open requests")
    table([r.__dict__ for r in manager.maintenance_requests], ["description", "contact"])

# ---- Hiring ----
with tabs[6]:
    st.header("Hiring / HR")
    hr_action = st.selectbox("Action", options=["hire", "fire"], key="hr_action")
    position = st.text_input("Position", placeholder="e.g., Line Cook", key="hr_position")
    boards = st.text_input("Boards (comma-separated)", placeholder="Indeed, Craigslist, Company Site", key="hr_boards")
    if st.button("Record HR update", key="hr_record"):
        b = [x.strip() for x in boards.split(",") if x.strip()]
        if position.strip() and b:
            manager.post_job_update(hr_action, position.strip(), b)
            log("hr_update", {"action": hr_action, "position": position.strip(), "boards": b})
            st.success("Recorded.")
        else:
            st.error("Position and at least one board required.")
    st.subheader("History")
    table([j.__dict__ for j in manager.job_postings], ["action", "position", "boards"])

# ---- Finance ----
with tabs[7]:
    st.header("Finance")
    st.caption("Simple revenue/expense tracking + P&L.")
    cA, cB = st.columns(2)
    with cA:
        st.subheader("Revenue")
        sale = st.number_input("Add sale", min_value=0.0, value=0.0, step=10.0, key="sale_amt")
        if st.button("Record sale", key="sale_btn"):
            if sale > 0:
                manager.record_sale(float(sale))
                log("record_sale", {"amount": float(sale)})
                st.success("Recorded.")
            else:
                st.error("Sale must be > 0")
    with cB:
        st.subheader("Expenses")
        expense = st.number_input("Add expense", min_value=0.0, value=0.0, step=10.0, key="exp_amt")
        if st.button("Record expense", key="exp_btn"):
            if expense > 0:
                manager.record_expense(float(expense))
                log("record_expense", {"amount": float(expense)})
                st.success("Recorded.")
            else:
                st.error("Expense must be > 0")
    st.divider()
    st.subheader("Profit & Loss")
    rev, exp, prof = manager.generate_pnl()
    m1, m2, m3 = st.columns(3)
    m1.metric("Revenue", f"${rev:,.2f}")
    m2.metric("Expenses", f"${exp:,.2f}")
    m3.metric("Profit", f"${prof:,.2f}")

# ---- AI Ops ----
with tabs[8]:
    st.header("AI Ops")
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.subheader("Ask about your restaurant")
        st.caption("Try: *What should I reorder this week?* — the assistant can propose changes, "
                   "but nothing is applied until you approve it.")
        st.session_state.setdefault("chat_history", [])
        st.session_state.setdefault("pending_actions", [])

        if not cfg.anthropic_api_key:
            st.warning("Set ANTHROPIC_API_KEY to enable the assistant.")
        question = st.text_input("Your question", placeholder="What should I reorder this week?", key="ai_question")
        if st.button("Ask AI", key="ai_ask_btn", disabled=not cfg.anthropic_api_key):
            q = question.strip()
            if not q:
                st.error("Ask a question.")
            else:
                with st.spinner("Thinking..."):
                    try:
                        reply = ask(make_client(cfg.anthropic_api_key), cfg.anthropic_model, q,
                                    build_state_block(manager, store), st.session_state.chat_history)
                        st.session_state.chat_history += [("You", q), ("AI", reply.text)]
                        st.session_state.pending_actions = reply.actions
                        log("ai_ask", {"question": q, "model": cfg.anthropic_model, "proposed": len(reply.actions)})
                    except Exception as e:  # network / auth / rate-limit
                        st.error(f"AI error: {type(e).__name__}: {e}")

        pending = st.session_state.pending_actions
        if pending:
            st.subheader("Proposed changes")
            for a in pending:
                err = validate_action(a)
                st.write(("⚠️ " + err) if err else "• " + describe_action(a))
            ap, dis = st.columns(2)
            if ap.button("Approve & apply", key="ai_apply_btn", width="stretch"):
                results = execute_actions(manager, store, pending)
                store.save(manager)
                st.session_state.pending_actions = []
                st.success("Done.")
                st.write(results)
            if dis.button("Discard", key="ai_discard_btn", width="stretch"):
                st.session_state.pending_actions = []
                log("ai_actions_discarded", {"count": len(pending)})
                st.rerun()

        st.divider()
        for role, msg in st.session_state.chat_history[-20:]:
            st.markdown(f"**{role}:** {msg}")

    with right:
        st.subheader("Upload files")
        label = st.selectbox("What is this file mostly about?", [
            "Auto-detect (recommended)", "Menu / pricing", "Vendor invoices / price sheets",
            "Inventory counts", "Sales reports (daily/weekly/monthly)", "Payroll / labor", "Other"],
            key="ingest_choice")
        uploaded = st.file_uploader("Upload files", type=["pdf", "png", "jpg", "jpeg", "csv", "txt"],
                                    accept_multiple_files=True, key="upload_files")
        st.caption("Files are stored and queued for ingest. Automatic sorting into dashboard sections is coming next.")
        if uploaded:
            done = set(st.session_state.setdefault("uploaded_seen", set()))
            new = [f for f in uploaded if (f.name, f.size) not in done]
            saved = 0
            for f in new:
                if f.size > MAX_UPLOAD_MB * 1024 * 1024:
                    st.error(f"{f.name} exceeds {MAX_UPLOAD_MB} MB.")
                    continue
                store.save_upload(f.name, f.getvalue(), label)
                st.session_state.uploaded_seen.add((f.name, f.size))
                saved += 1
            if saved:
                log("upload_files", {"count": saved, "label": label})
                st.success(f"Queued {saved} file(s) for ingest.")

# ---- Audit & Export ----
with tabs[9]:
    st.header("Audit & Export")
    st.subheader("Audit log")
    st.dataframe(store.load_audit(400), width="stretch", hide_index=True)
    st.subheader("Export")
    e1, e2, e3 = st.columns(3)
    if store.audit_path.exists():
        e1.download_button("Download audit_log.jsonl", store.audit_path.read_bytes(), "audit_log.jsonl",
                           "application/jsonl", width="stretch")
    else:
        e1.info("No audit log yet.")
    if store.vendor_history_path.exists():
        e2.download_button("Download vendor_price_history.csv", store.vendor_history_path.read_bytes(),
                           "vendor_price_history.csv", "text/csv", width="stretch")
    else:
        e2.info("No vendor history yet.")
    e3.download_button("Download Accountant ZIP", store.export_zip(manager),
                       f"restaurant_export_{date.today().isoformat()}.zip", "application/zip",
                       width="stretch")

st.caption("Changes are persisted when you click **Save data** (AI-approved actions save automatically).")
