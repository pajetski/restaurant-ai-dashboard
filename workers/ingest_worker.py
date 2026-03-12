"""Ingestion worker scaffold for processing supplier invoice uploads from a JSONL queue.

This module intentionally defines only the worker boundary and next implementation steps.
"""

import json
from pathlib import Path
from typing import Any

QUEUE_PATH = Path("upload_queue.jsonl")


def _read_queue_records(queue_path: Path) -> list[dict[str, Any]]:
    """Read JSONL queue records safely from disk."""
    if not queue_path.exists():
        return []

    records: list[dict[str, Any]] = []
    with queue_path.open("r", encoding="utf-8") as queue_file:
        for line_number, raw_line in enumerate(queue_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON at line {line_number} in {queue_path}.")
                continue

            if not isinstance(record, dict):
                print(f"Skipping non-object JSON at line {line_number} in {queue_path}.")
                continue

            records.append(record)

    return records


def _references_pdf(record: dict[str, Any]) -> bool:
    """Return True when a queue record appears to reference a PDF upload."""
    record_text = json.dumps(record, ensure_ascii=False).lower()
    return ".pdf" in record_text


def _record_label(record: dict[str, Any]) -> str:
    """Extract a path-like label from a queue record for display."""
    for key in ("path", "file_path", "filepath", "filename", "file", "name", "upload_path"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return "<path-or-filename-unavailable>"


def main() -> None:
    """Run the ingestion worker entrypoint."""
    queue_records = _read_queue_records(QUEUE_PATH)
    pdf_records = [record for record in queue_records if _references_pdf(record)]

    print(f"Total queue records: {len(queue_records)}")
    print(f"Total PDF records: {len(pdf_records)}")

    for record in pdf_records:
        print(f"PDF record: {_record_label(record)}")

    # TODO: Call ReceivingService.parse_supplier_invoice_pdf() for each PDF item.
    # TODO: Log parsing and ingestion results.
    # TODO: Mark processed queue records as completed.


if __name__ == "__main__":
    main()
