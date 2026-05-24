"""
Module to provide database utils.
"""

import pathlib

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import create_engine

from ..config import DB_DIR, DB_FILE
from . import tables

sync_engine: Engine | None = None
async_engine: AsyncEngine | None = None


def init_db():
    """Initialize the database and create tables if they don't exist."""

    global sync_engine, async_engine

    _ = tables  # make sure all models are imported before creating tables
    from sqlmodel import SQLModel

    if pathlib.Path(DB_DIR).exists() is False:
        pathlib.Path(DB_DIR).mkdir(parents=True)
    sync_engine = create_engine(f"sqlite:///{DB_DIR}/{DB_FILE}")
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{DB_DIR}/{DB_FILE}", echo=True)

    SQLModel.metadata.create_all(sync_engine)

    # migrate: add category column to documents table if missing
    _migrate_documents(sync_engine)


def _migrate_documents(engine):
    """Add category column to existing documents table."""
    try:
        from sqlalchemy import inspect

        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("documents")]
        if "category" not in columns:
            with engine.connect() as conn:
                conn.exec_driver_sql(
                    "ALTER TABLE documents ADD COLUMN category VARCHAR DEFAULT '未分类'"
                )
                conn.commit()
    except Exception:
        pass  # table may not exist yet, that's fine
