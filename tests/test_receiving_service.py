import json
import tempfile
import unittest
from pathlib import Path

from services.receiving.parser import SupplierInvoicePdfParser
from services.receiving.service import ReceivingIntakeService


class FakeParser(SupplierInvoicePdfParser):
    def extract_text(self, pdf_path: Path) -> str:  # pragma: no cover - deterministic fixture
        return """Supplier: Fresh Foods Co
Invoice #: INV-1001
Invoice Date: 2026-02-10
Tomatoes 10 2.50 25.00
Cheese 5 4.00 20.00
Total: 45.00
"""


class ReceivingIntakeServiceTests(unittest.TestCase):
    def test_parse_supplier_invoice_pdf_returns_expected_fields(self) -> None:
        service = ReceivingIntakeService(parser=FakeParser())

        payload = service.parse_supplier_invoice_pdf("fake_invoice.pdf")

        self.assertEqual(payload["vendor_name"], "Fresh Foods Co")
        self.assertEqual(payload["invoice_number"], "INV-1001")
        self.assertEqual(payload["invoice_date"], "2026-02-10")
        self.assertEqual(payload["total_amount"], 45.0)
        self.assertEqual(len(payload["line_items"]), 2)

    def test_parse_to_json_file_writes_json(self) -> None:
        service = ReceivingIntakeService(parser=FakeParser())

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "parsed.json"
            payload = service.parse_to_json_file("fake_invoice.pdf", output)

            self.assertTrue(output.exists())
            parsed_file = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(parsed_file["invoice_number"], payload["invoice_number"])


if __name__ == "__main__":
    unittest.main()
