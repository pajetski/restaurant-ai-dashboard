# AGENTS.md

## Product
This repository is for CAKE, an operations platform, with DUDE as the AI GM layer.
DUDE stands for Data, Understanding, Direction, Execution.
The product must create real operational value through data intake, normalization,
alerts, recommendations, and workflow execution.

## Non-negotiable goals
- Build a real software system, not a thin wrapper around an LLM.
- Prefer durable architecture over fast hacks.
- Every feature must improve operational decision-making, automation, or execution.
- Keep the system modular so it can start in restaurants and expand later.

## Architecture rules
- Separate ingestion, domain models, business logic, integrations, AI services, and UI.
- Do not couple prompts directly to routes or UI components.
- All external systems must use adapter interfaces.
- Use typed schemas for all core entities and payloads.
- Favor deterministic rules first, AI second.
- Add tests for business logic and parsing behavior.

## Initial product scope
- Receiving PDF intake first
- Toast-first integration path
- Inventory and vendor normalization
- Alerts for price spikes, missing items, and low-stock risk
- Manager dashboard summaries
- Leave room for later smartphone scan workflows

## Working rules
- Before major code changes, write or update architecture notes in /docs.
- When adding a module, include a README or docstring explaining purpose and boundaries.
- Run lint/tests before marking work complete.
- Prefer small, reviewable pull requests.
- If assumptions are required, write them down explicitly.