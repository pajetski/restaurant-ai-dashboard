# Restaurant Ops Dashboard

Streamlit dashboard for running a restaurant's back office in one place: menu/price sync across
platforms, hours, vendor price tracking with cost-creep detection, weekly order compilation,
maintenance log, hiring log, simple P&L, and an AI assistant (Claude) that answers questions
about your data and *proposes* changes you approve.

## Quick start

```bash
cp .env.example .env      # add ANTHROPIC_API_KEY (and APP_PASSWORD)
./run.sh
```

## Layout

| Path | Purpose |
|---|---|
| `dashboard.py` | Streamlit UI only |
| `restaurant_ops/manager.py` | Domain model + logic (no I/O) |
| `restaurant_ops/storage.py` | Atomic JSON state, audit log, vendor history, uploads, export |
| `restaurant_ops/llm.py` | Claude assistant; actions come back as a schema-checked tool call |
| `restaurant_ops/actions.py` | Validation + execution of approved AI actions |
| `restaurant_ops/analytics.py` | Cost-creep detection, prompt context |
| `tests/` | Unit tests + Streamlit UI smoke tests |

## Configuration (env vars)

| Var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Enables the AI assistant |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | |
| `APP_PASSWORD` | – | Shared login. **Required** when `APP_ENV=production` |
| `APP_ENV` | `development` | `production` refuses to start without a password |
| `DATA_DIR` | `data` | All runtime data. Mount a persistent volume here |

Runtime data (`data/`) is git-ignored — never commit real business data.

## Tests

```bash
pip install -r requirements-dev.txt && python -m pytest
```

## Deploy

```bash
docker build -t restaurant-ops .
docker run -p 8501:8501 -v ops-data:/data \
  -e ANTHROPIC_API_KEY=... -e APP_PASSWORD=... restaurant-ops
```

Put it behind HTTPS (Fly.io, Render, Railway, or a reverse proxy) — the shared password is sent
over the wire.

## Known gaps before real production use

- **Storage is a single JSON file**: fine for one instance / one user; move to Postgres (e.g. Supabase) for multi-user or multi-instance.
- **Auth is one shared password**: move to per-user login with roles.
- **Uploads are stored but not yet ingested**: next step is Claude vision/PDF parsing into vendor prices, menu and sales, with the same approve-before-apply flow.
- **No real integrations yet** (POS, DoorDash, payroll, job boards): platforms are records, not live syncs.
- **Finance is running totals**, not dated transactions — needed for real P&L periods.
