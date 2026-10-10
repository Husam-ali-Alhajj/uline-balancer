"""Test setup. The environment is configured BEFORE the app is imported:
a throw-away SQLite database and the inline executor (runs finish inside the request)."""

import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["RUN_EXECUTOR"] = "inline"

import pytest  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
CONTRACTS = BACKEND.parent / "contracts"


@pytest.fixture(scope="session")
def client():
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from alembic import command

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")  # also tests that the migration works

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
