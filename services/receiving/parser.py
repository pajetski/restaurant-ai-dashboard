"""PDF extraction and deterministic supplier invoice parsing.

This module uses PyPDF to extract text and then applies regex-based parsing
rules for invoice headers and line items.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from .models import ParsedInvoiceDocument, ParsedInvoiceLine


_AMOUNT_PATTERN = re.compile(r"(?:\$\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)")
_INVOICE_NO_PATTERN = re.compile(r"invoice\s*(?:#|number|no\.?):?\s*([A-Z0-9\-]+)", re.IGNORECASE)
_DATE_PATTERN = re.compile(r"(?:invoice\s*date|date):?\s*([0-9]{1,4}[\-/][0-9]{1,2}[\-/][0-9]{1,4})", re.IGNORECASE)
_TOTAL_PATTERN = re.compile(r"(?:total\s*(?:due|amount)?):?\s*\$?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", re.IGNORECASE)
_VENDOR_PATTERN = re.compile(r"(?:vendor|supplier|from):\s*(.+)", re.IGNORECASE)


class SupplierInvoicePdfParser:
    """Parse supplier invoice PDFs into `ParsedInvoiceDocument` payloads."""

    def extract_text(self, pdf_path: Path) -> str:
        """Extract text from all pages of a PDF file using PyPDF."""
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("pypdf is required for PDF parsing. Install with `pip install pypdf`.") from exc

        reader = PdfReader(str(pdf_path))
        pages: List[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)

    def parse(self, pdf_path: str | Path) -> ParsedInvoiceDocument:
        """Parse a PDF path into a deterministic parsed invoice structure."""
        path = Path(pdf_path)
        text = self.extract_text(path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        document = ParsedInvoiceDocument(
            source_file=str(path),
            raw_text_preview=text[:2000],
        )

        joined = "\n".join(lines)
        document.invoice_number = self._extract_first(_INVOICE_NO_PATTERN, joined)
        document.invoice_date = self._extract_first(_DATE_PATTERN, joined)
        document.vendor_name = self._extract_vendor(lines)
        document.total_amount = self._extract_amount(_TOTAL_PATTERN, joined)
        document.line_items = self._extract_line_items(lines)

        if not document.invoice_number:
            document.parse_warnings.append("invoice_number_not_found")
        if not document.invoice_date:
            document.parse_warnings.append("invoice_date_not_found")
        if not document.vendor_name:
            document.parse_warnings.append("vendor_name_not_found")
        if document.total_amount is None:
            document.parse_warnings.append("total_amount_not_found")
        if not document.line_items:
            document.parse_warnings.append("line_items_not_found")

        return document

    @staticmethod
    def _extract_first(pattern: re.Pattern[str], text: str) -> Optional[str]:
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_amount(pattern: re.Pattern[str], text: str) -> Optional[float]:
        raw = SupplierInvoicePdfParser._extract_first(pattern, text)
        if not raw:
            return None
        return float(raw.replace(",", ""))

    @staticmethod
    def _extract_vendor(lines: List[str]) -> Optional[str]:
        for line in lines[:30]:
            match = _VENDOR_PATTERN.search(line)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_line_items(lines: List[str]) -> List[ParsedInvoiceLine]:
        """Best-effort parse of tabular-like line items from extracted text lines."""
        parsed: List[ParsedInvoiceLine] = []
        for line in lines:
            normalized = " ".join(line.split())
            amounts = _AMOUNT_PATTERN.findall(normalized)
            lowered = normalized.lower()
            if lowered.startswith(("total", "subtotal", "tax", "invoice", "date", "vendor", "supplier")):
                continue

            if len(amounts) < 2:
                continue

            # Heuristic: description precedes first numeric token.
            first_num = _AMOUNT_PATTERN.search(normalized)
            if not first_num:
                continue
            description = normalized[: first_num.start()].strip(" -:\t")
            if len(description) < 2:
                continue

            quantity = SupplierInvoicePdfParser._to_float(amounts[0])
            unit_price = SupplierInvoicePdfParser._to_float(amounts[1]) if len(amounts) > 1 else None
            line_total = SupplierInvoicePdfParser._to_float(amounts[2]) if len(amounts) > 2 else None

            parsed.append(
                ParsedInvoiceLine(
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

        return parsed

    @staticmethod
    def _to_float(value: str) -> Optional[float]:
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
