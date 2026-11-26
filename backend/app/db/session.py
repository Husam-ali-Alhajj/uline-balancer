from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import config

_url = config.database_url()
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}
# A GA worker process imports this module fresh, after the executor marked it, and gets a smaller pool.
if config.IN_WORKER:
    _pool = {"pool_size": config.DB_WORKER_POOL_SIZE, "max_overflow": config.DB_WORKER_MAX_OVERFLOW}
else:
    _pool = {"pool_size": config.DB_POOL_SIZE, "max_overflow": config.DB_MAX_OVERFLOW}
engine = create_engine(_url, pool_pre_ping=True, connect_args=_connect_args, **_pool)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with SessionLocal() as session:
        yield session
