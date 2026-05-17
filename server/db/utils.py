from typing import AsyncGenerator

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

import server.db


def get_session():
    """FastAPI dependency to get a synchronous database session."""
    if server.db.sync_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() on application startup.")
    with Session(server.db.sync_engine) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an asynchronous database session."""
    if server.db.async_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() on application startup.")

    async_session_maker = sessionmaker(bind=server.db.async_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore

    async with async_session_maker() as session:  # type: ignore
        yield session
