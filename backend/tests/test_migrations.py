"""Migration 0003 (owner_id) goes up and down on SQLite and leaves 0001 and 0002 intact."""

from alembic.config import Config
from conftest import BACKEND
from sqlalchemy import create_engine, inspect

from alembic import command


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _shape(url: str):
    found = inspect(create_engine(url))
    return {c["name"] for c in found.get_columns("runs")}, {i["name"] for i in found.get_indexes("runs")}


def test_owner_id_upgrade_and_downgrade(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = _config(url)

    command.upgrade(cfg, "head")
    columns, indexes = _shape(url)
    assert "owner_id" in columns
    assert "ix_runs_owner_id_created_at" in indexes

    command.downgrade(cfg, "0002")
    columns, indexes = _shape(url)
    assert "owner_id" not in columns
    assert "ix_runs_owner_id_created_at" not in indexes
    assert {"id", "status", "input", "created_at"} <= columns and "ix_runs_status" in indexes

    command.upgrade(cfg, "head")
    assert "owner_id" in _shape(url)[0]
