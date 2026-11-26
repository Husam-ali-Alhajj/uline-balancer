# Backend

Python 3.12, FastAPI, SQLAlchemy 2, Alembic. See `../MASTER.md` for the full picture.

## Run it locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # Windows: copy .env.example .env
alembic upgrade head                 # creates the tables (SQLite file by default)
uvicorn app.main:app --reload        # http://localhost:8000/docs
```

**Run exactly one uvicorn process** (no `--workers` above 1, here or in deployment). The cap on
active runs (`MAX_ACTIVE_RUNS`) is enforced with a lock inside the process, so two server processes
could each accept runs up to the cap. The GA itself still uses several processes
(`MAX_WORKER_PROCESSES`), started by the one server process.

## Check your work (run before every pull request)

```bash
ruff check .
pytest
```

## Layout

| Folder | Purpose | Rule |
|---|---|---|
| `app/api/` | HTTP endpoints, error format | thin: no business logic |
| `app/schemas/` | Pydantic models = the API contract | must match `../contracts/` |
| `app/services/` | run lifecycle, solver glue | the only place that connects API, GA and DB |
| `app/ga/` | the genetic algorithm | PURE Python, no web/DB imports |
| `app/ml/` | recommender interface, rule-based version | PURE Python |
| `app/db/` | SQLAlchemy models and session | tables change only via Alembic |
| `alembic/versions/` | migrations | never edit a merged migration |
| `ml_training/` | ML training scripts (AI engineer) | not imported by `app/` |

## Database changes

```bash
alembic revision -m "describe the change"   # then edit the new file in alembic/versions/
alembic upgrade head
```
Never change tables by hand in the Supabase dashboard.

## Using Supabase

Optional. Without it, the app uses a local SQLite file.

### Setup

1. In the Supabase dashboard, open the project's connection settings and copy the **session pooler** string.
2. Put it in `backend/.env` (never in git, chat or a screenshot):

   ```
   DATABASE_URL=postgresql://postgres.<project-ref>:<url-encoded-password>@<pooler-host>:5432/postgres?sslmode=require
   ```

   URL-encode special characters in the password (for example `@` becomes `%40`). Save the file.
3. From `backend/`, with the virtual environment active:

   ```bash
   alembic upgrade head
   alembic current                  # should show: 0001 (head)
   uvicorn app.main:app
   ```

Run only one server against the same database. Every server start marks all `queued` and `running` runs as
failed (`server_restarted`), including runs that belong to another server.

### Which connection string

| Connection | Port | Use |
|---|---|---|
| Session pooler | 5432 | Yes, locally and on a server. Works over IPv4 and with prepared statements. |
| Direct | 5432 | Only from a network with IPv6; the host has no IPv4 address on the free plan. |
| Transaction pooler | 6543 | No. psycopg prepares repeated statements and this mode does not support them. |

### Problems and what to do

- **Project paused.** Free projects pause after about a week of low activity. Open the project in the dashboard,
  press Resume or Restore and wait until it is healthy (possible for up to one year after the pause). This is the
  likely cause of the failed first connection on 2026-11-24: a timeout, then
  `(EAUTHQUERY) ... connection to database not available`.
- **`(ECIRCUITBREAKER) ... new connections are temporarily blocked`.** Caused by repeated failed attempts. Stop
  retrying, fix the cause and wait a few minutes.
- **SSL.** Without `sslmode`, the driver uses `prefer`, which may fall back to an unencrypted connection. Use
  `sslmode=require`. It enforces encryption but does not verify the server certificate.
- **IPv6.** If the direct host cannot be resolved or reached, the network has no IPv6. Use the session pooler.
- **Timezone.** The database runs in UTC and timestamps are stored with a timezone. Nothing to configure.
- **`No module named 'app'`.** Run alembic from `backend/`; `alembic.ini` adds that folder to the import path.
- **Connection limit.** Each process (the server and every GA worker) can open up to 15 connections (pool 5 plus
  overflow 10). Supabase documents a default pool of 15 for the free plan. Check the project's value in the dashboard.
- **Latency.** With about 300 ms per round trip, `GET /runs/{id}` takes about 1.1 s. Progress is written from a
  background thread, so the GA does not wait for the database. Host the backend close to the database region.
- **Server killed during a run.** The worker process can stay alive after a hard kill. It does not overwrite the
  failed run, but end it by hand.

### Access

Row level security is enabled on `runs` with no policies, and the public `anon` and `authenticated` roles have no
privileges on it. The backend connects as the table owner. The `service_role` key bypasses row level security: keep it secret.
