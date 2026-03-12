# D.U.D.E. Restaurant AI — Current State

## Project

Restaurant AI Operations Dashboard
Codename: **D.U.D.E. (Data Understanding Direction Execution)**

Repository:
restaurant_ai_dashboard

---

# Current System Status

Working components:

• Streamlit dashboard UI (`dashboard.py`)
• Restaurant manager logic (`restaurant_ai_app.py`)
• Vendor price tracking
• Supplier invoice parser (`services/receiving/service.py`)
• File upload system
• Vendor price history logging
• Local AI assistant via Ollama

Dashboard launches with:

python3 -m streamlit run dashboard.py

---

# Current Development Branch

foundation/professionalize-dude

Active PR:

Add ingestion pipeline + automation foundation

---

# Current Goal

Build the **first automated backend ingestion pipeline**

Target file:

workers/ingest_worker.py

Purpose:

Automatically process uploaded supplier invoices.

Pipeline goal:

Upload File
↓
upload_queue.jsonl
↓
ingest_worker.py
↓
ReceivingService parser
↓
vendor_prices database
↓
vendor price history

---

# Next Tasks

1. Build `workers/ingest_worker.py`
2. Normalize supplier item names
3. Add inventory tracking
4. Build reorder recommendation engine
5. Integrate POS data (Toast or Square)

---

# Future Vision

D.U.D.E becomes an **AI Restaurant Operating System** capable of:

• Food cost tracking
• Vendor price monitoring
• Automatic invoice ingestion
• Inventory prediction
• AI reorder recommendations
• POS analytics

Target users:

Independent restaurants and multi-location operators.

---

# Notes for Codex / AI Agents

Focus on **small isolated tasks**.

Do not refactor unrelated files.

Prefer adding modules inside:

services/
workers/
docs/

Keep the dashboard functional during development.


# DUDE Current State

## Purpose
This document records the current state of the repository before structural refactor work begins.

## Current repo condition
The repository currently contains a working Streamlit-based application and related runtime files, but it does not yet reflect the intended professional module structure for DUDE.

## Observed characteristics
- `dashboard.py` currently holds important app behavior and likely mixes UI and business logic
- runtime and state artifacts exist in the repository
- architecture planning documents now exist under `/docs`
- the repository has not yet been refactored into a modular product structure

## Immediate constraints
- avoid breaking current working behavior
- avoid large rewrites
- preserve useful existing logic where possible
- move toward a modular architecture in controlled steps

## Near-term refactor goals
- identify which parts of current application code are UI-specific
- identify which parts contain business logic
- identify which parts should eventually move into:
  - domain
  - ingestion
  - normalization
  - rules
  - recommendations
  - integrations
  - config
- create a migration path rather than a destructive rewrite

## Known non-doc changes currently present
- `dashboard.py` is modified
- `audit_log.jsonl` is modified
- `dashboard_before_global_sidebar.py` is untracked
- `uploads/` is untracked

These should remain separate from documentation and architecture commits unless intentionally addressed later.