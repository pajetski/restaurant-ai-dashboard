# DUDE Architecture

## Purpose
This document defines the intended software architecture for DUDE.

DUDE is an AI operations platform designed to ingest messy business data, normalize it, evaluate it, generate recommendations, and support execution.

The architecture must support a restaurant-first product while remaining extensible to other operations-heavy businesses later.

## Architectural principles
- Keep core business logic deterministic where possible
- Separate business logic from UI and external integrations
- Design for modular growth
- Prefer adapters and service boundaries over tightly coupled code
- Keep the system testable and production-minded

## Core layers

### 1. Ingestion
Responsible for collecting raw operational data from external sources.

Examples:
- receiving PDFs
- spreadsheet / Excel imports
- POS feeds
- menu data
- scheduling data

### 2. Normalization
Responsible for converting raw external data into canonical DUDE entities.

Examples:
- vendor normalization
- item name matching
- SKU mapping
- unit normalization
- menu item mapping

### 3. Domain
Defines the core business entities and their meaning.

Examples:
- Location
- Vendor
- InventoryItem
- MenuItem
- Invoice
- InvoiceLineItem
- ReceivingEvent
- SalesEvent
- ScheduleEvent
- Alert
- Recommendation
- Forecast

### 4. Rules
Contains deterministic business logic used to evaluate data and identify issues.

Examples:
- missing invoice fields
- price spike detection
- low-stock alerts
- scheduling bottleneck checks
- menu change impact checks

### 5. Forecasting
Responsible for projecting likely future conditions from historical data.

Examples:
- inventory depletion prediction
- reorder timing
- labor pressure windows
- menu-driven purchasing shifts

### 6. Recommendations
Turns system understanding into suggested actions.

Examples:
- suggested order quantities
- staffing adjustments
- menu-driven purchasing changes
- issue prioritization

### 7. Execution
Handles downstream operational follow-through.

Examples:
- alert publishing
- task generation
- exports
- sync actions
- manager summaries

### 8. Integrations
Defines adapter boundaries for external systems.

Examples:
- Toast
- spreadsheet import/export
- email
- Slack
- future POS systems

### 9. App / API
Provides user-facing and programmatic access to DUDE functionality.

Examples:
- dashboard views
- APIs
- future background jobs
- admin tools

## Repository direction
The repository should evolve toward a structure that clearly separates:
- domain models
- ingestion
- normalization
- rules
- forecasting
- recommendations
- execution
- integrations
- config
- app / API
- tests
- docs

## Near-term build priority
The first implementation priority is to establish the professional software foundation for:
- receiving PDF intake
- spreadsheet compatibility
- Toast integration boundaries
- inventory normalization
- alerts and recommendations

## Long-term build direction
DUDE should eventually support:
- menu change awareness
- business hours change awareness
- scheduling bottleneck detection
- historical forecasting
- broader workflow automation
- expansion into other operational business types