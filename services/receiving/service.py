"""Orchestration service for receiving PDF intake.

This service provides a stable API for parsing supplier invoice PDFs and
writing parsed payloads to JSON for downstream workflows.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .parser import SupplierInvoicePdfParser

VENDOR_PRICE_HISTORY_PATH = Path("vendor_price_history.csv")
VENDOR_PRICE_HISTORY_FIELDS = [
    "vendor_name",
    "item_name",
    "unit_price",
    "quantity",
    "invoice_date",
    "source_file",
]


class ReceivingIntakeService:
    """Application-facing service for receiving invoice document parsing."""

    def __init__(self, parser: Optional[SupplierInvoicePdfParser] = None) -> None:
        self._parser = parser or SupplierInvoicePdfParser()

    def parse_supplier_invoice_pdf(self, pdf_path: str | Path) -> Dict[str, Any]:
        """Parse a supplier invoice PDF and return JSON-serializable payload."""
        parsed = self._parser.parse(pdf_path)
        payload = parsed.to_dict()
        self._append_vendor_price_history_rows(payload)
        return payload

    def parse_to_json_file(self, pdf_path: str | Path, output_path: str | Path) -> Dict[str, Any]:
        """Parse invoice PDF and write parsed payload to a JSON file."""
        payload = self.parse_supplier_invoice_pdf(pdf_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def _append_vendor_price_history_rows(self, payload: Dict[str, Any]) -> None:
        """Append parsed invoice line items to vendor price history CSV."""
        line_items = payload.get("line_items")
        if not isinstance(line_items, list) or not line_items:
            return

        rows: list[dict[str, Any]] = []
        vendor_name = payload.get("vendor_name")
        invoice_date = payload.get("invoice_date")
        source_file = payload.get("source_file")

        for line_item in line_items:
            if not isinstance(line_item, dict):
                continue

            rows.append(
                {
                    "vendor_name": vendor_name,
                    "item_name": line_item.get("description"),
                    "unit_price": line_item.get("unit_price"),
                    "quantity": line_item.get("quantity"),
                    "invoice_date": invoice_date,
                    "source_file": source_file,
                }
            )

        if not rows:
            return

        VENDOR_PRICE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_header = not VENDOR_PRICE_HISTORY_PATH.exists() or VENDOR_PRICE_HISTORY_PATH.stat().st_size == 0

        with VENDOR_PRICE_HISTORY_PATH.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=VENDOR_PRICE_HISTORY_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)
