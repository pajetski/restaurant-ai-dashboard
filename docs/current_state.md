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