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

    if not pathlib.Path(DB_DIR).exists():
        pathlib.Path(DB_DIR).mkdir(parents=True)
    
    # 创建同步引擎
    sync_engine = create_engine(f"sqlite:///{DB_DIR}/{DB_FILE}")
    
    # 创建异步引擎 - 使用 create_async_engine 而不是 create_engine
    async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_DIR}/{DB_FILE}", 
        echo=True, 
        future=True
    ) # type: ignore 

    SQLModel.metadata.create_all(sync_engine)
    
    print(f"✅ Database initialized at {DB_DIR}/{DB_FILE}")


# 添加 getter 函数，确保每次都能获取到正确的引擎（即使模块被重新加载）
def get_sync_engine() -> Engine:
    """Get sync engine, initializing if needed."""
    global sync_engine
    if sync_engine is None:
        init_db()
    return sync_engine  # type: ignore


def get_async_engine() -> AsyncEngine:
    """Get async engine, initializing if needed."""
    global async_engine
    if async_engine is None:
        init_db()
    return async_engine  # type: ignore