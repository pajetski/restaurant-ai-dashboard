# DUDE Foundation Professionalization Plan

## Scope
This note captures the current state of the repository, major architectural risks, and a staged implementation plan for DUDE's first operational capability without large rewrites.

## 1) Current architecture summary

### Repository shape
Current top-level contents are:
- `dashboard.py` — primary Streamlit application with UI, upload handling, AI chat, action execution, audit export, and persistence helpers
- `restaurant_ai_app.py` — proof-of-concept domain-like class (`RestaurantManager`) and dataclasses for platforms, maintenance, and job updates
- `docs/` — product, architecture, domain, roadmap, and current-state notes
- `run.sh` — local bootstrap script that creates a venv and launches Streamlit
- `audit_log.jsonl` — runtime state artifact tracked in repository

### Functional behavior present today
- Streamlit app with operational tabs (platforms, menu, hours, vendors, weekly order, maintenance, hiring, finance, AI ops, audit/export)
- File upload queueing into `uploads/` with metadata in `upload_queue.jsonl`
- Flat-file persistence (`data.json`, `audit_log.jsonl`, `vendor_price_history.csv`)
- Optional local LLM call via Ollama endpoint in UI flow
- Vendor cost history and basic cost-creep detection

### Documentation posture
Product-level docs are present and aligned with DUDE goals (`architecture`, `domain_model`, `roadmap`, `product_vision`), but code structure has not yet been aligned to those layers.

## 2) Architecture risks and structural gaps

### A. Layering and coupling risks
1. **UI and business logic are tightly coupled** in `dashboard.py`.
2. **Execution logic is mixed with orchestration and presentation** (AI action parsing/execution lives next to UI widgets).
3. **Integration details are in app code** rather than behind adapters/ports.

### B. Domain modeling risks
1. Current code model is **restaurant demo-oriented** and not yet the normalized operational domain described in docs.
2. No typed canonical models yet for first intake wedge (`Invoice`, `InvoiceLineItem`, `ReceivingEvent`, normalized `Vendor` and `InventoryItem`).

### C. Data and reliability risks
1. Flat files are useful for prototyping but risky for scale (concurrency, traceability guarantees, migration complexity).
2. Runtime artifacts are co-located with source; environment boundaries are not formalized.
3. No explicit schema-version strategy for persisted records.

### D. Extensibility and integration risks
1. No clear ingestion pipeline boundaries (`source -> raw document -> parsed fields -> normalized entities -> rules`).
2. Toast integration boundary not yet represented as an interface with contract tests/fakes.
3. Missing package-level module boundaries for future background jobs and APIs.

### E. Quality and operations risks
1. No test suite currently present for business rules, parsing, or integration contracts.
2. No first-class configuration module for environment-specific settings.

## 3) Prioritized implementation plan (first operational capability)

### Priority 0 — establish architecture scaffolding (no destructive rewrite)
Create package skeleton while leaving current Streamlit behavior intact:

```text
src/dude/
  app/
  domain/
    models/
  ingestion/
    pdf/
    spreadsheet/
  normalization/
  rules/
  recommendations/
  forecasting/
  execution/
  integrations/
    toast/
  config/
  storage/

tests/
  unit/
  contracts/
  fixtures/
```

Notes:
- Keep `dashboard.py` functioning; begin moving logic behind thin service calls.
- Add README/docstrings at module boundaries.

### Priority 1 — normalized domain models (restaurant-first)
Implement typed models for the first wedge:
- `Location`
- `Vendor`
- `InventoryItem`
- `Invoice`
- `InvoiceLineItem`
- `ReceivingEvent`
- `SourceDocument` (to preserve traceability to raw files)

Also define:
- IDs and timestamps policy
- status enums (`parsed`, `normalized`, `failed_validation`)
- provenance fields (`source_system`, `source_document_id`, `ingested_at`)

### Priority 2 — PDF intake pipeline (supplier invoices / receiving docs)
Implement deterministic, auditable flow:
1. **Intake**: store file + metadata (`sha256`, size, mime, uploaded_by/time)
2. **Classification**: invoice vs receiving doc vs unknown
3. **Extraction**: parser interface + initial heuristic parser (with placeholders for OCR/provider adapters)
4. **Validation**: required-field checks (invoice number/date/vendor/line items)
5. **Normalization**: map extracted data to canonical models
6. **Persistence**: write normalized record + parse issues + raw extraction payload
7. **Rule triggers**: run deterministic checks (missing fields, price spikes)

Key boundary:
- `PdfParserPort` interface and explicit parse result schema (`success`, `confidence`, `warnings`, `fields`).

### Priority 3 — Toast-first integration boundaries
Create integration contract before implementation depth:
- `ToastPort` interface with methods such as:
  - `fetch_sales_events(start, end)`
  - `fetch_menu_items()`
  - `fetch_business_hours()`
- Add adapter placeholder:
  - `ToastApiAdapter` (real API)
  - `ToastFakeAdapter` (tests/dev)
- Normalize Toast payloads into domain events in `normalization/`.

### Priority 4 — minimal deterministic rules for operational value
Start with a few high-signal, deterministic checks:
- invoice missing required fields
- vendor price increase threshold breach
- receiving quantity mismatch vs invoice

Output standardized `Alert` entities and store results with evidence references.

## 4) First small, safe commits recommended

### Commit 1 (first recommended)
**Title:** `docs: add concrete foundation implementation plan for pdf intake and toast boundaries`

**Contents:**
- Add this document.
- No behavior changes.

**Why first:**
- Aligns team on architecture before code movement.
- Respects current-state guidance to avoid destructive rewrites.

### Commit 2
**Title:** `chore: add src/dude package skeleton with module READMEs`

**Contents:**
- Create `src/dude/...` folders with minimal `__init__.py` and boundary README/docstrings.
- No functional migration yet.

### Commit 3
**Title:** `feat(domain): add typed restaurant-first core models for intake wedge`

**Contents:**
- Add typed models and validation helpers for invoice/receiving flow.
- Add focused unit tests for model validation and serialization.

### Commit 4
**Title:** `feat(ingestion): add pdf intake service interface and queue processor scaffold`

**Contents:**
- Add intake service and parser port contracts.
- Add fixture-based tests for parser contract and validation behavior.

## Assumptions
- Current Streamlit behavior must remain operable during early refactor.
- PDF parsing providers may vary; parser must be interface-driven.
- Deterministic rule outputs are prioritized over AI-generated decisions in core workflows.
