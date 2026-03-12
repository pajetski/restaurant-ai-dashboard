"""CLI for parsing supplier invoice PDFs into JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import ReceivingIntakeService


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse supplier invoice PDF into JSON")
    parser.add_argument("pdf", help="Path to supplier invoice PDF")
    parser.add_argument(
        "--out",
        help="Output JSON path (default: <pdf>.parsed.json)",
        default=None,
    )
    args = parser.parse_args()

    input_path = Path(args.pdf)
    output_path = Path(args.out) if args.out else input_path.with_suffix(".parsed.json")

    service = ReceivingIntakeService()
    service.parse_to_json_file(input_path, output_path)
    print(f"Parsed invoice JSON written to: {output_path}")


if __name__ == "__main__":
    main()
