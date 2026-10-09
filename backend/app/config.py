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
