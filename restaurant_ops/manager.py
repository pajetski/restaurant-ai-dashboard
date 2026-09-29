"""Domain model: platforms, vendors, maintenance, HR, finance.

Pure data + logic. No printing, no UI, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Platform:
    name: str
    menu: Dict[str, float] = field(default_factory=dict)
    hours: str = ""


@dataclass
class MaintenanceRequest:
    description: str
    contact: str


@dataclass
class JobPosting:
    action: str  # 'hire' or 'fire'
    position: str
    boards: List[str]


class RestaurantManager:
    def __init__(self) -> None:
        self.platforms: List[Platform] = []
        self.vendor_prices: Dict[str, Dict[str, float]] = {}
        self.maintenance_requests: List[MaintenanceRequest] = []
        self.job_postings: List[JobPosting] = []
        self.revenue: List[float] = []
        self.expenses: List[float] = []
        self.orders: List[Dict[str, Any]] = []

    # --- platforms / menu / hours ---
    def add_platform(self, name: str, menu: Optional[Dict[str, float]] = None, hours: str = "") -> None:
        self.platforms.append(Platform(name=name, menu=dict(menu or {}), hours=hours))

    def update_menu_item(self, item: str, price: float) -> None:
        for p in self.platforms:
            p.menu[item] = price

    def set_business_hours(self, hours: str) -> None:
        for p in self.platforms:
            p.hours = hours

    def menu_items(self) -> List[str]:
        return sorted({k for p in self.platforms for k in p.menu})

    # --- vendors ---
    def set_vendor_price(self, vendor: str, item: str, price: float) -> None:
        self.vendor_prices.setdefault(vendor, {})[item] = price

    def add_vendor_prices(self, vendor: str, prices: Dict[str, float]) -> None:
        self.vendor_prices[vendor] = dict(prices)

    def vendor_items(self) -> List[str]:
        return sorted({k for v in self.vendor_prices.values() for k in (v or {})})

    def compare_prices(self, items: List[str]) -> Dict[str, Tuple[str, float]]:
        """Cheapest (vendor, price) per item; items with no price data are omitted."""
        results: Dict[str, Tuple[str, float]] = {}
        for item in items:
            offers = [(price_list[item], vendor) for vendor, price_list in self.vendor_prices.items() if item in price_list]
            if offers:
                price, vendor = min(offers)
                results[item] = (vendor, price)
        return results

    def compile_weekly_order(self, items: List[str]) -> Dict[str, List[Tuple[str, float]]]:
        order: Dict[str, List[Tuple[str, float]]] = {}
        for item, (vendor, price) in self.compare_prices(items).items():
            order.setdefault(vendor, []).append((item, price))
        return order

    # --- maintenance / HR ---
    def report_maintenance_issue(self, description: str, contact: str) -> None:
        self.maintenance_requests.append(MaintenanceRequest(description, contact))

    def post_job_update(self, action: str, position: str, boards: List[str]) -> None:
        if action not in {"hire", "fire"}:
            raise ValueError("action must be 'hire' or 'fire'")
        self.job_postings.append(JobPosting(action, position, list(boards)))

    # --- finance ---
    def record_sale(self, amount: float) -> None:
        self.revenue.append(amount)

    def record_expense(self, amount: float) -> None:
        self.expenses.append(amount)

    def generate_pnl(self) -> Tuple[float, float, float]:
        rev, exp = sum(self.revenue), sum(self.expenses)
        return rev, exp, rev - exp

    # --- (de)serialisation ---
    def to_dict(self) -> Dict[str, Any]:
        return {
            "platforms": [{"name": p.name, "menu": p.menu, "hours": p.hours} for p in self.platforms],
            "vendor_prices": self.vendor_prices,
            "maintenance_requests": [{"description": r.description, "contact": r.contact} for r in self.maintenance_requests],
            "job_postings": [{"action": j.action, "position": j.position, "boards": j.boards} for j in self.job_postings],
            "revenue": self.revenue,
            "expenses": self.expenses,
            "orders": self.orders,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RestaurantManager":
        m = cls()
        for p in d.get("platforms", []):
            m.add_platform(p["name"], p.get("menu", {}), p.get("hours", ""))
        m.vendor_prices = d.get("vendor_prices") or {}
        m.maintenance_requests = [MaintenanceRequest(**r) for r in d.get("maintenance_requests", [])]
        m.job_postings = [JobPosting(**j) for j in d.get("job_postings", [])]
        m.revenue = [float(x) for x in d.get("revenue", [])]
        m.expenses = [float(x) for x in d.get("expenses", [])]
        m.orders = list(d.get("orders", []))
        return m

    @classmethod
    def sample(cls) -> "RestaurantManager":
        m = cls()
        m.add_platform("POS", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
        m.add_platform("Website", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
        m.add_platform("DeliveryApp", {"Burger": 11.99, "Fries": 4.49}, "10am–9pm")
        m.add_vendor_prices("VendorA", {"Grenadine": 12.00, "Plastic Cups": 8.50, "Beef": 5.25})
        m.add_vendor_prices("VendorB", {"Grenadine": 11.50, "Plastic Cups": 9.00, "Beef": 5.75, "Wine": 14.00})
        m.add_vendor_prices("VendorC", {"Grenadine": 12.25, "Plastic Cups": 8.00, "Beef": 5.50, "Wine": 13.50})
        return m
