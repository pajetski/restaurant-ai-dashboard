# DUDE Roadmap

## Purpose
This document defines the phased build plan for DUDE.

The goal is to build DUDE as a professional operations platform with a durable software foundation, while implementing features in a controlled sequence.

DUDE stands for:
Data. Understanding. Direction. Execution.

## Product strategy
DUDE starts with restaurant operations as the first wedge, but should be designed so the underlying architecture can support broader operations-heavy businesses later.

The roadmap should prioritize:
- durable architecture
- real operational value
- deterministic business logic
- modular integrations
- gradual expansion of automation and forecasting

## Phase 1: Foundation and first operational value

### Goals
- establish professional software structure
- define core domain model
- support initial ingestion workflows
- create deterministic alerting and recommendation foundations

### Target capabilities
- repository structure cleanup
- docs and architecture foundation
- restaurant-first domain entities
- receiving PDF intake foundation
- spreadsheet / Excel compatibility foundation
- Toast integration boundaries
- vendor and inventory normalization
- initial alerts for:
  - price spikes
  - missing items
  - low-stock risk
- initial recommendation scaffolding

### Deliverables
- product docs
- architecture docs
- domain model docs
- structured package layout
- config and environment handling
- basic tests
- initial adapters and boundaries

## Phase 2: Operational intelligence

### Goals
- expand from intake into business understanding
- connect historical data to forecasts and recommendations
- improve manager usefulness

### Target capabilities
- inventory forecasting using historical usage and sales
- order recommendation logic
- menu change tracking
- hours change tracking
- scheduling bottleneck detection
- anomaly detection for operational drift
- richer manager summaries

### Deliverables
- forecasting module
- recommendation engine
- menu and hours change event models
- schedule analysis logic
- additional tests and validation coverage

## Phase 3: Execution and automation

### Goals
- turn system understanding into operational execution
- automate follow-through where appropriate

### Target capabilities
- outbound notifications
- email / Slack / webhook alert delivery
- task generation
- sync actions into connected systems where appropriate
- more complete operational dashboards
- background jobs and worker processes

### Deliverables
- execution module
- delivery adapters
- worker/job foundations
- operational action logging
- more advanced monitoring and reporting

## Phase 4: Product hardening

### Goals
- make DUDE reliable enough for broader real-world use
- prepare for production-grade operation

### Target capabilities
- persistence and database hardening
- authentication and role support
- observability and logging improvements
- deployment readiness
- multi-location support
- stronger integration reliability

### Deliverables
- hardened data layer
- auth and access control foundations
- production configuration standards
- deployment and runtime documentation

## Build discipline
At every phase, DUDE should prioritize:
- small, reviewable changes
- tests for business logic
- clear documentation
- modular boundaries
- deterministic systems first
- AI augmentation second

## What not to do
- do not build a thin chatbot wrapper and call it a platform
- do not over-prioritize UI polish before architecture
- do not hardcode core business logic into prompts
- do not tightly couple integrations to the domain layer
- do not expand scope without first preserving structure

## Immediate next milestone
The next milestone after documentation is to refactor the repository toward a clean module layout and implement the first restaurant-first domain models in code.