# AGENTS.md

## Product
This repository is for DUDE, an AI operations platform.

DUDE stands for:
Data. Understanding. Direction. Execution.

DUDE must create real operational value through:
- intake of business data from PDFs, spreadsheets, POS systems, menu systems, and scheduling sources
- normalization of messy operational data into canonical business entities
- deterministic rules, forecasts, alerts, and recommendations
- workflow execution and operational follow-through

DUDE starts with restaurant operations but should be architected so it can expand into other operations-heavy businesses later.

## Non-negotiable goals
- Build a real software product, not a thin wrapper around an LLM.
- Prefer durable architecture over fast hacks.
- Every feature must improve operational decision-making, automation, forecasting, or execution.
- Keep the system modular and extensible.
- Favor systems that are testable, reviewable, and production-minded.

## Core product capabilities
The platform foundation must eventually support:
- receiving PDF intake
- spreadsheet / Excel import
- Toast-first POS integration
- menu change tracking
- business hours change tracking
- scheduling bottleneck detection
- inventory prediction using historical data
- ordering recommendations
- alerts and workflow execution
- manager-facing summaries and operational direction

## Architecture rules
- Separate ingestion, normalization, domain models, business logic, forecasting, recommendation logic, integrations, execution, and UI.
- Do not couple prompts directly to routes, UI components, or business rules.
- All external systems must use adapter or port interfaces.
- Use typed schemas or typed models for all core entities and payloads.
- Favor deterministic rules first, AI second.
- Add tests for business logic, parsing behavior, and forecasting logic.
- Preserve a path for future API, background workers, and production deployment.

## Initial build priorities
- establish professional repository structure
- define product docs and architecture docs
- define core restaurant-first domain model
- support receiving PDF intake first
- support spreadsheet import compatibility
- create Toast integration boundaries
- create deterministic rules and alerting foundation
- leave room for forecasting and recommendation systems

## Working rules
- Before major code changes, write or update architecture notes in /docs.
- When adding a module, include a docstring or README explaining purpose and boundaries.
- Prefer small, reviewable pull requests or commits.
- Run tests before marking work complete.
- Write down assumptions explicitly.
- Avoid unnecessary rewrites.
- Do not prioritize UI polish over system architecture.