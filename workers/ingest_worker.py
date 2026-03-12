"""Ingestion worker scaffold for processing supplier invoice uploads from a JSONL queue.

This module intentionally defines only the worker boundary and next implementation steps.
"""

from pathlib import Path

QUEUE_PATH = Path("upload_queue.jsonl")


def main() -> None:
    """Run the ingestion worker entrypoint."""
    # TODO: Read queue records from QUEUE_PATH.
    # TODO: Filter queue records to PDF uploads.
    # TODO: Call ReceivingService.parse_supplier_invoice_pdf() for each PDF item.
    # TODO: Log parsing and ingestion results.
    # TODO: Mark processed queue records as completed.
    pass


if __name__ == "__main__":
    main()
