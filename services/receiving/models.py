"""Typed models for parsed receiving invoice payloads.

These models represent the parsed output layer between ingestion and
normalization. They are intentionally lightweight and serializable to JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


@dataclass
class ParsedInvoiceLine:
    """A raw parsed invoice line with minimal typed numeric fields."""

    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None


@dataclass
class ParsedInvoiceDocument:
    """Deterministic parsed representation of a supplier invoice PDF."""

    source_file: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: str = "USD"
    line_items: List[ParsedInvoiceLine] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)
    raw_text_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return asdict(self)
