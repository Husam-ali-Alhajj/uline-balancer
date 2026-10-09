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
