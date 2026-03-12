"""Ingestion worker scaffold for processing supplier invoice uploads from a JSONL queue.

This module intentionally defines only the worker boundary and next implementation steps.
"""

import json
from pathlib import Path
from typing import Any

from services.receiving.service import ReceivingIntakeService

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


def _record_filename(record: dict[str, Any]) -> str:
    """Extract the original filename from a queue record."""
    filename = record.get("filename")
    if isinstance(filename, str) and filename.strip():
        return filename
    return ""


def _record_stored_path(record: dict[str, Any]) -> str:
    """Extract stored file path from a queue record."""
    stored_as = record.get("stored_as")
    if isinstance(stored_as, str) and stored_as.strip():
        return stored_as
    return ""


def _record_sha256(record: dict[str, Any]) -> str:
    """Extract sha256 digest from a queue record."""
    sha256 = record.get("sha256")
    if isinstance(sha256, str) and sha256.strip():
        return sha256.lower()
    return ""


def main() -> None:
    """Run the ingestion worker entrypoint."""
    queue_records = _read_queue_records(QUEUE_PATH)
    pdf_records = [record for record in queue_records if _references_pdf(record)]

    skipped_menu_records = 0
    unique_invoice_like_records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for record in pdf_records:
        filename = _record_filename(record)
        if "menu" in filename.lower():
            skipped_menu_records += 1
            continue

        stored_as = _record_stored_path(record)
        sha256 = _record_sha256(record)

        if not filename or not stored_as or not sha256:
            continue

        if sha256 in seen_hashes:
            continue

        seen_hashes.add(sha256)
        unique_invoice_like_records.append(record)

    print(f"Total queue records: {len(queue_records)}")
    print(f"Total PDF records: {len(pdf_records)}")
    print(f"Total skipped menu records: {skipped_menu_records}")
    print(f"Total unique invoice-like PDF records: {len(unique_invoice_like_records)}")

    intake_service = ReceivingIntakeService()

    for record in unique_invoice_like_records:
        display_name = _record_filename(record)
        stored_as = _record_stored_path(record)

        print(f"Processing record: {display_name} | stored path: {stored_as}")
        try:
            intake_service.parse_supplier_invoice_pdf(stored_as)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to parse {display_name} ({stored_as}): {exc}")

    # TODO: Log parsing and ingestion results.
    # TODO: Mark processed queue records as completed.


if __name__ == "__main__":
    main()
