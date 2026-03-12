# Receiving PDF Intake Foundation

## Purpose
This note defines the first implementation slice for DUDE receiving intake: deterministic parsing of supplier invoice PDFs into structured JSON.

## Scope of this step
- Add a modular `services/receiving` package.
- Parse invoice PDFs using **PyPDF** text extraction.
- Convert extracted content into a typed parsed-invoice structure.
- Output parsed payloads to JSON for downstream normalization/rules.

## Boundaries
- This step does **not** perform OCR or external AI extraction.
- This step does **not** normalize into final canonical domain entities yet.
- This step does **not** integrate directly with dashboard routes/UI.

## Module responsibilities
- `services/receiving/parser.py`: PDF text extraction and deterministic field parsing.
- `services/receiving/models.py`: typed parsed-invoice payload models.
- `services/receiving/service.py`: orchestration API for parse + JSON output.
- `services/receiving/cli.py`: small CLI entry point for manual processing.

## Deterministic parsing assumptions
- Invoice-like lines can be detected by simple regex patterns.
- Header fields (invoice number/date/vendor/total) may appear in free text and are extracted heuristically.
- Line items are parsed when rows contain an item label and numeric amount.

## Next steps after this foundation
1. Add provider adapters (pdfplumber/OCR) behind extraction interfaces.
2. Add normalization into `Invoice`, `InvoiceLineItem`, and `ReceivingEvent` entities.
3. Add validation/rules for missing fields and price anomalies.
4. Integrate with upload queue processor.
