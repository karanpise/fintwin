# FinTwin production configuration review

This document records repository configuration only. No Render service or
production database was queried or changed.

## Service entry points and ports

The active Streamlit entry point is `frontend/Dashboard.py`. Render and the
local `run.py` launcher now reference this path; the removed `frontend/app.py`
path was stale. The API entry point is `backend.main:app`.

Render starts each web service on its injected `$PORT`, listening on
`0.0.0.0`. The API liveness check is `/health`; it does not depend on database
availability. `/health/database` is the readiness probe and returns HTTP 503
when `SELECT 1` fails. The Streamlit service obtains `FINTWIN_API_URL` from the
API service URL. Locally, the frontend defaults to `http://127.0.0.1:8000` and
`run.py` starts the API on port 8000 and Streamlit on port 8501.

Render's API start command runs `alembic upgrade head` before Uvicorn. A
migration failure prevents the API from starting. Review each migration and
preflight existing data before deployment; this audit did not execute
migrations.

## Environment configuration

Required secret values are supplied through the runtime environment and must
not be committed or printed:

- `DATABASE_URL`: PostgreSQL connection string; Render maps its managed
  database connection string to this name.
- `JWT_SECRET_KEY`: signing secret; Render generates this value in
  `render.yaml`.

Other settings read by the backend are `APP_ENV`, `JWT_ALGORITHM`, and
`ACCESS_TOKEN_EXPIRE_MINUTES`. Render currently declares `production`, `HS256`,
and 30 minutes respectively. `APP_ENV` is read but does not currently select
different application behavior. The frontend reads `FINTWIN_API_URL`; Render
maps the API service URL to it. Local developers can copy `.env.example` and
must supply their own secret values without committing `.env`.

`requirements.txt` now pins the direct runtime dependencies to the versions
installed and tested under Python 3.13.5. `.python-version` pins that runtime;
`requirements-dev.txt` adds pytest and httpx for local tests. Transitive
dependencies are not fully locked, and no clean network install was run during
this audit.

## Database and schema observations

- The SQLAlchemy engine uses `pool_pre_ping=True`; pool sizing and connection
  timeouts use SQLAlchemy defaults. `get_db` closes each session. Profile
  updates commit per request, while failed commits close through dependency
  cleanup; registration explicitly rolls back on uniqueness conflicts.
- The profile has a unique `user_id` foreign key with cascade delete. The four
  legacy balance amounts remain non-null numeric columns for compatibility;
  reporting flags distinguish confirmed amounts (including explicit zero)
  from unconfirmed stored values. The provenance migration marks all existing
  balances unconfirmed while preserving their amounts. `monthly_savings` is
  nullable.
- A lower-case unique email index is represented in model metadata and a new
  migration. Before applying it to an existing database, check for conflicting
  rows with `SELECT lower(email), count(*) FROM users GROUP BY lower(email)
  HAVING count(*) > 1;`. The migration deliberately does not merge or rename
  accounts; existing conflicts must be resolved before migration.
- The balance-provenance migration's downgrade removes confirmation flags and
  loses all confirmation state. Export/review those flags before downgrade;
  avoid downgrading after users have confirmed balances unless the rollback
  process accounts for the old application's inability to interpret them.

## Known operational gaps

- There is no login or registration rate limiter in the current architecture.
- Financial-health, risk, simulation, optimizer, ML prediction, and root
  responses do not all have explicit response models. Health endpoints,
  authentication, and profile routes do. The dynamic projection and optimizer
  responses are especially valuable candidates for typed response models.
- CORS is not configured. Streamlit makes server-side HTTP requests, so the
  current application does not need browser cross-origin API calls; reassess
  before adding a browser-based client.
- The tests use in-memory SQLite for API behavior, not PostgreSQL. PostgreSQL
  migration execution, pool behavior, and concurrent registration on the
  managed service remain unverified.
