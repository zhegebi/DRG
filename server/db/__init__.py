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
