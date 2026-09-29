"""Read-only analysis helpers."""

from __future__ import annotations

import pandas as pd

from .manager import RestaurantManager

CREEP_COLUMNS = ["vendor", "item", "prev_price", "latest_price", "delta", "delta_pct", "time"]


def detect_cost_creep(df: pd.DataFrame, lookback_rows: int = 2000) -> pd.DataFrame:
    """For each vendor+item, compare the latest price to the previous one."""
    if df.empty:
        return pd.DataFrame(columns=CREEP_COLUMNS)
    d = df.tail(lookback_rows).copy()
    d["price"] = pd.to_numeric(d["price"], errors="coerce")
    d = d.dropna(subset=["price"]).sort_values("time", kind="stable")
    out = []
    for (vendor, item), g in d.groupby(["vendor", "item"]):
        if len(g) < 2:
            continue
        prev, latest = float(g.iloc[-2]["price"]), float(g.iloc[-1]["price"])
        out.append({
            "vendor": vendor, "item": item, "prev_price": prev, "latest_price": latest,
            "delta": latest - prev,
            "delta_pct": (latest - prev) / prev * 100.0 if prev else None,
            "time": g.iloc[-1]["time"],
        })
    if not out:
        return pd.DataFrame(columns=CREEP_COLUMNS)
    return pd.DataFrame(out).sort_values(["delta_pct", "delta"], ascending=False)


def build_context_summary(m: RestaurantManager) -> str:
    items = m.menu_items()
    preview = ", ".join(items[:20]) + ("..." if len(items) > 20 else "")
    rev, exp, profit = m.generate_pnl()
    return (
        f"Platforms: {', '.join(p.name for p in m.platforms) or 'none'}\n"
        f"Hours: {'; '.join(f'{p.name}={p.hours}' for p in m.platforms if p.hours) or 'none'}\n"
        f"Menu items: {preview or 'none'}\n"
        f"Revenue total: {rev:.2f}\nExpenses total: {exp:.2f}\nProfit total: {profit:.2f}\n"
        f"Vendors tracked: {', '.join(m.vendor_prices) or 'none'}\n"
    )
