"""
restaurant_ai_app.py
======================

This module implements a simple proof‑of‑concept command‑line application
designed for restaurant owners and managers. It demonstrates how common
operational tasks—such as synchronising menu changes across multiple
platforms, updating business hours, managing maintenance requests,
posting hiring or termination notices, comparing vendor prices, compiling
weekly order lists, and generating a rudimentary profit and loss (P&L)
statement—could be automated using Python. The goal is to illustrate
concepts rather than provide production‑ready code.

Each task is represented as a method on the ``RestaurantManager`` class,
which maintains internal state about platforms, vendors, and cost data.
Functionality is broken down into discrete steps to show how automation
could reduce repetitive manual work. For example, when updating a menu
item, the application iterates through all registered platforms and
applies the change uniformly. Similarly, the price comparison routine
aggregates prices from a simulated set of vendors and recommends the
cheapest source for each item.

Note: This implementation uses simple data structures and prints actions
to the console for demonstration purposes. In a real‑world deployment
these operations would integrate with APIs (e.g., POS systems, vendor
portals, HR platforms) and include robust error handling, authentication,
and data persistence.

To run the module interactively, execute it as a script:

    python restaurant_ai_app.py

You will be presented with a menu of operations to explore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import sys


@dataclass
class Platform:
    """Represents a sales or listing platform (e.g. POS, delivery app, website)."""
    name: str
    menu: Dict[str, float] = field(default_factory=dict)
    hours: str = ""

    def update_menu_item(self, item: str, price: float) -> None:
        """Update a menu item's price on this platform."""
        self.menu[item] = price

    def set_hours(self, hours: str) -> None:
        """Set business hours on this platform."""
        self.hours = hours


@dataclass
class MaintenanceRequest:
    """Represents a maintenance task and the party responsible for fixing it."""
    description: str
    contact: str  # e.g. plumber, electrician


@dataclass
class JobPosting:
    """Represents a hiring or termination update across multiple job boards."""
    action: str  # 'hire' or 'fire'
    position: str
    boards: List[str]


class RestaurantManager:
    """
    Core class that coordinates operations across platforms, vendors and
    internal accounting. All methods either modify internal state or
    compute summaries based on stored data.
    """

    def __init__(self) -> None:
        self.platforms: List[Platform] = []
        # Vendor pricing structured as {vendor: {item: price}}
        self.vendor_prices: Dict[str, Dict[str, float]] = {}
        # Collected maintenance requests
        self.maintenance_requests: List[MaintenanceRequest] = []
        # Collected job postings or notices
        self.job_postings: List[JobPosting] = []
        # Basic financial tracking
        self.revenue: List[float] = []
        self.expenses: List[float] = []

    # --- Platform management methods ---
    def add_platform(self, name: str, menu: Optional[Dict[str, float]] = None,
                     hours: str = "") -> None:
        """Register a new platform with an optional initial menu and hours."""
        if menu is None:
            menu = {}
        self.platforms.append(Platform(name=name, menu=dict(menu), hours=hours))

    def update_menu_item(self, item: str, price: float) -> None:
        """
        Apply a menu price change across all platforms. Prints a summary of
        updates for user visibility.
        """
        for p in self.platforms:
            p.update_menu_item(item, price)
            print(f"Updated {item} to ${price:.2f} on {p.name}")

    def set_business_hours(self, hours: str) -> None:
        """Apply new business hours across all platforms."""
        for p in self.platforms:
            p.set_hours(hours)
            print(f"Updated business hours to '{hours}' on {p.name}")

    # --- Maintenance management methods ---
    def report_maintenance_issue(self, description: str, contact: str) -> None:
        """
        Record a maintenance issue and specify who needs to be contacted. In a
        production system this would dispatch notifications.
        """
        req = MaintenanceRequest(description=description, contact=contact)
        self.maintenance_requests.append(req)
        print(f"Logged maintenance: '{description}' → notify {contact}")

    # --- Hiring/Firing management methods ---
    def post_job_update(self, action: str, position: str, boards: List[str]) -> None:
        """
        Record a hiring or termination action and list all boards where it
        needs to be posted. This demonstrates consolidation of duplicate work.
        """
        if action not in {"hire", "fire"}:
            raise ValueError("action must be 'hire' or 'fire'")
        posting = JobPosting(action=action, position=position, boards=list(boards))
        self.job_postings.append(posting)
        verb = "Hiring for" if action == "hire" else "Terminating"
        for board in boards:
            print(f"{verb} {position} via {board}")

    # --- Vendor price management methods ---
    def add_vendor_prices(self, vendor: str, prices: Dict[str, float]) -> None:
        """
        Register or update a vendor's price list. Prices should be a mapping
        from item names to cost per unit.
        """
        self.vendor_prices[vendor] = dict(prices)

    def compare_prices(self, items: List[str]) -> Dict[str, Tuple[str, float]]:
        """
        For each requested item, determine the vendor offering the lowest price.
        Returns a mapping of item → (best_vendor, best_price). Also prints a
        summary to the console.
        """
        results: Dict[str, Tuple[str, float]] = {}
        for item in items:
            best_vendor = None
            best_price = float('inf')
            for vendor, price_list in self.vendor_prices.items():
                if item in price_list and price_list[item] < best_price:
                    best_price = price_list[item]
                    best_vendor = vendor
            if best_vendor is None:
                print(f"No price data available for {item}")
            else:
                results[item] = (best_vendor, best_price)
                print(f"Best price for {item}: ${best_price:.2f} from {best_vendor}")
        return results

    def compile_weekly_order(self, items: List[str]) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a weekly order list by choosing the cheapest vendor for each item.
        Returns a mapping of vendor → list of (item, price).
        """
        order: Dict[str, List[Tuple[str, float]]] = {}
        price_summary = self.compare_prices(items)
        for item, (vendor, price) in price_summary.items():
            order.setdefault(vendor, []).append((item, price))
        print("Compiled weekly order:")
        for vendor, items_list in order.items():
            subtotal = sum(price for _, price in items_list)
            item_str = ", ".join([f"{i} (${p:.2f})" for i, p in items_list])
            print(f"  {vendor}: {item_str} → subtotal ${subtotal:.2f}")
        return order

    # --- Financial management methods ---
    def record_sale(self, amount: float) -> None:
        """Record revenue from a sale."""
        self.revenue.append(amount)
        print(f"Recorded revenue: ${amount:.2f}")

    def record_expense(self, amount: float) -> None:
        """Record an expense."""
        self.expenses.append(amount)
        print(f"Recorded expense: ${amount:.2f}")

    def generate_pnl(self) -> Tuple[float, float, float]:
        """
        Generate a simple profit and loss statement by summing recorded
        revenues and expenses. Returns a tuple (total_revenue, total_expenses,
        profit) and prints a summary.
        """
        total_rev = sum(self.revenue)
        total_exp = sum(self.expenses)
        profit = total_rev - total_exp
        print(f"\nP&L Summary:")
        print(f"  Total revenue: ${total_rev:.2f}")
        print(f"  Total expenses: ${total_exp:.2f}")
        print(f"  Profit/Loss: ${profit:.2f}\n")
        return total_rev, total_exp, profit


def demo() -> None:
    """
    Run a demonstration sequence to showcase functionality. This function
    registers sample data, performs typical operations, and prints results
    to the console. It's invoked when running this file as a script.
    """
    manager = RestaurantManager()
    # Add sample platforms
    manager.add_platform("POS", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
    manager.add_platform("Website", {"Burger": 9.99, "Fries": 3.49}, "10am–10pm")
    manager.add_platform("DeliveryApp", {"Burger": 11.99, "Fries": 4.49}, "10am–9pm")

    print("Initial platforms registered.\n")
    # Update menu item across all platforms
    manager.update_menu_item("Fries", 3.99)
    # Update business hours
    manager.set_business_hours("11am–9pm")
    # Report maintenance issue
    manager.report_maintenance_issue("Walk‑in cooler not cooling properly", "Refrigeration contractor")
    # Post hiring and firing notices
    manager.post_job_update("hire", "Line Cook", ["Indeed", "Craigslist", "Company Site"])
    manager.post_job_update("fire", "Dishwasher", ["Internal HR system"])
    # Add vendor pricing
    manager.add_vendor_prices("VendorA", {"Grenadine": 12.00, "Plastic Cups": 8.50, "Beef": 5.25})
    manager.add_vendor_prices("VendorB", {"Grenadine": 11.50, "Plastic Cups": 9.00, "Beef": 5.75, "Wine": 14.00})
    manager.add_vendor_prices("VendorC", {"Grenadine": 12.25, "Plastic Cups": 8.00, "Beef": 5.50, "Wine": 13.50})
    # Compare prices and compile weekly order
    manager.compile_weekly_order(["Grenadine", "Plastic Cups", "Beef", "Wine"])
    # Record some sales and expenses
    manager.record_sale(1500.00)
    manager.record_sale(2000.00)
    manager.record_expense(500.00)  # food cost
    manager.record_expense(800.00)  # labor cost
    manager.record_expense(300.00)  # utilities
    # Generate P&L
    manager.generate_pnl()


if __name__ == "__main__":
    demo()


