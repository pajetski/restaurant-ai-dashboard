"""Orchestration service for receiving PDF intake.

This service provides a stable API for parsing supplier invoice PDFs and
writing parsed payloads to JSON for downstream workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .parser import SupplierInvoicePdfParser


class ReceivingIntakeService:
    """Application-facing service for receiving invoice document parsing."""

    def __init__(self, parser: Optional[SupplierInvoicePdfParser] = None) -> None:
        self._parser = parser or SupplierInvoicePdfParser()

    def parse_supplier_invoice_pdf(self, pdf_path: str | Path) -> Dict[str, Any]:
        """Parse a supplier invoice PDF and return JSON-serializable payload."""
        parsed = self._parser.parse(pdf_path)
        return parsed.to_dict()

    def parse_to_json_file(self, pdf_path: str | Path, output_path: str | Path) -> Dict[str, Any]:
        """Parse invoice PDF and write parsed payload to a JSON file."""
        payload = self.parse_supplier_invoice_pdf(pdf_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
