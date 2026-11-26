"""Settings, read from environment variables (and an optional backend/.env file)."""

import os

from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    """DATABASE_URL, normalised for SQLAlchemy 2 + psycopg 3.

    Local default is a SQLite file so nobody needs Supabase just to run the app.
    For Supabase use the Postgres connection string from the dashboard.
    """
    url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
RUN_EXECUTOR = os.environ.get("RUN_EXECUTOR", "process")  # "process" or "inline" (tests)
MAX_WORKER_PROCESSES = int(os.environ.get("MAX_WORKER_PROCESSES", "2"))
MAX_ACTIVE_RUNS = int(os.environ.get("MAX_ACTIVE_RUNS", "4"))
MAX_RUN_SECONDS = float(os.environ.get("MAX_RUN_SECONDS", "60"))
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", "1000000"))

# Database connections per process (SQLAlchemy pool_size + max_overflow). The server serves the API;
# a GA worker needs one connection at a time. Total = server + MAX_WORKER_PROCESSES x worker, which
# must stay well under the Supabase pooler limit (15 on the free plan). Defaults: 3 + 2 and 1 + 0.
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "3"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "2"))
DB_WORKER_POOL_SIZE = int(os.environ.get("DB_WORKER_POOL_SIZE", "1"))
DB_WORKER_MAX_OVERFLOW = int(os.environ.get("DB_WORKER_MAX_OVERFLOW", "0"))
IN_WORKER = False  # set to True in GA worker processes by services/executor.py
