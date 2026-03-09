# services/receiving

## Purpose
The `services/receiving` package provides DUDE's first receiving intake foundation:
- parse supplier invoice PDFs
- produce deterministic parsed payloads
- export those payloads as JSON for downstream normalization and rules

## Boundaries
- This package focuses on ingestion parsing only.
- It does not contain UI code.
- It does not perform full canonical normalization yet.

## Modules
- `models.py`: typed parsed payload models
- `parser.py`: PyPDF text extraction + deterministic regex parsing
- `service.py`: orchestration API for parse + JSON output
- `cli.py`: command-line execution entry point
